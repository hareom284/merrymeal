"""Story 5.4 — payment event handlers (webhook side effects).

Three pure functions, one per Stripe event the webhook view dispatches:

* ``apply_checkout_completed`` — one-time gift just succeeded.
* ``apply_invoice_paid``       — recurring charge succeeded.
* ``apply_subscription_deleted`` — recurring donor cancelled (Story 5.7).

All three are **idempotent**. Re-firing the same event must not:

* Create a duplicate ``Donation`` row.
* Double-count the campaign progress bar
  (``apps.donations.services.campaigns.raised_cents_for``).

Idempotency is enforced two ways:

* The DB-level safety net: ``Donation.transaction_id`` is ``unique=True``
  (Story 5.2 migration). A second insert with the same ``transaction_id``
  would raise ``IntegrityError``.
* The app-level fast path: ``select_for_update()`` + early-return when
  the row already exists or has already advanced past ``pending``.

Service writes are wrapped in ``transaction.atomic()`` so a partial
failure rolls back rather than leaving a half-flipped row.
"""

from __future__ import annotations

from django.db import transaction

from apps.donations.models import Campaign, Donation

# ----------------------------------------------------------------------
# checkout.session.completed (one-time)
# ----------------------------------------------------------------------

@transaction.atomic
def apply_checkout_completed(session: dict) -> Donation:
    """Flip the pending ``Donation`` referenced by ``session`` to completed.

    The session object's ``metadata.donation_id`` was stamped by
    :func:`apps.donations.services.stripe_checkout.create_checkout_session`,
    so we can locate the row deterministically. The session's ``id``
    becomes the ``transaction_id`` (the idempotency hinge).

    Returns the ``Donation`` after the update.
    """
    session_id = session["id"]
    metadata = session.get("metadata") or {}
    donation_id = metadata.get("donation_id")
    subscription_id = session.get("subscription")  # set when mode=subscription

    # Fast idempotency path: have we already processed this session?
    already = (
        Donation.objects
        .select_for_update()
        .filter(transaction_id=session_id)
        .first()
    )
    if already is not None and already.status == "completed":
        return already

    if donation_id:
        donation = (
            Donation.objects
            .select_for_update()
            .filter(pk=donation_id)
            .first()
        )
        if donation is None:
            # Defensive: metadata pointed at a row that no longer exists.
            # Fall through to the upsert branch below.
            donation_id = None

    if donation_id:
        donation.status = "completed"
        donation.transaction_id = session_id
        if subscription_id and not donation.stripe_subscription_id:
            donation.stripe_subscription_id = subscription_id
        donation.save(
            update_fields=[
                "status",
                "transaction_id",
                "stripe_subscription_id",
                "updated_at",
            ]
        )
        return donation

    # Last-resort upsert: no usable metadata link. Use ``transaction_id``
    # as the dedupe key. ``update_or_create`` short-circuits a re-fire.
    donation, _ = Donation.objects.update_or_create(
        transaction_id=session_id,
        defaults={
            "status": "completed",
            "payment_type": "card",
            # campaign + donor_email are required NOT NULL; if we hit
            # this branch the session payload must carry them or the row
            # cannot exist. In practice every MerryMeal Checkout session
            # is created via Story 5.3 which stamps ``metadata``, so
            # this branch is a belt-and-braces fallback only.
            "campaign": Campaign.objects.get(slug="general-fund"),
            "donor_email": (session.get("customer_email") or ""),
            "amount_cents": int(session.get("amount_total") or 0),
        },
    )
    return donation


# ----------------------------------------------------------------------
# invoice.paid (recurring)
# ----------------------------------------------------------------------

@transaction.atomic
def apply_invoice_paid(invoice: dict) -> Donation:
    """Recurring charge — flip the pending row or create a new one.

    Stripe sends ``invoice.paid`` for **every** monthly charge:

    * **First invoice** — the pending ``Donation`` created by Story 5.3
      already has ``stripe_subscription_id`` set. Flip it to completed
      and stamp ``transaction_id`` with the invoice id.
    * **Subsequent invoices** — create a brand-new ``Donation`` row
      linked by ``stripe_subscription_id``.

    Idempotency hinges on ``transaction_id=invoice_id`` being unique.
    """
    invoice_id = invoice["id"]
    subscription_id = invoice.get("subscription")
    amount = int(invoice["amount_paid"])
    email = invoice.get("customer_email") or ""

    # Fast idempotency path: already processed this invoice?
    existing = (
        Donation.objects
        .select_for_update()
        .filter(transaction_id=invoice_id)
        .first()
    )
    if existing is not None:
        return existing

    # First-invoice path: the pending row carries the subscription id.
    pending = (
        Donation.objects
        .select_for_update()
        .filter(
            stripe_subscription_id=subscription_id,
            status="pending",
        )
        .first()
    )
    if pending is not None:
        pending.status = "completed"
        pending.transaction_id = invoice_id
        pending.save(
            update_fields=["status", "transaction_id", "updated_at"]
        )
        return pending

    # Subsequent-invoice path: clone shape from any sibling row.
    sibling = (
        Donation.objects
        .filter(stripe_subscription_id=subscription_id)
        .order_by("created_at")
        .first()
    )
    if sibling is not None:
        campaign = sibling.campaign
        donor_email = email or sibling.donor_email
    else:
        # Defensive default — no sibling means this webhook fired before
        # we ever saw the subscription. Bucket the gift into the general
        # fund so the receipt + campaign total still line up.
        campaign = Campaign.objects.get(slug="general-fund")
        donor_email = email

    return Donation.objects.create(
        campaign=campaign,
        donor_email=donor_email,
        amount_cents=amount,
        payment_type="card",
        status="completed",
        is_recurring=True,
        stripe_subscription_id=subscription_id,
        transaction_id=invoice_id,
    )


# ----------------------------------------------------------------------
# customer.subscription.deleted (Story 5.7 hook)
# ----------------------------------------------------------------------

@transaction.atomic
def apply_subscription_deleted(subscription: dict) -> int:
    """Mark every Donation linked to ``subscription`` as cancelled.

    Returns the number of rows updated — useful for the audit log
    breadcrumb the webhook view writes.

    ``cancelled`` (rather than ``refunded``) preserves the historical
    receipts: the donor really did receive their meals; cancellation
    only stops future charges.
    """
    sub_id = subscription["id"]
    return (
        Donation.objects
        .filter(stripe_subscription_id=sub_id)
        .exclude(status="cancelled")  # don't churn rows already cancelled
        .update(status="cancelled")
    )
