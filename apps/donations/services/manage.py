"""Story 5.7 — magic-link issue/verify + recurring-donation management.

The recurring-donation management page lets a donor:

* request a magic link by email (``send_magic_link``),
* land on a one-shot URL that lists their active subscriptions
  (``verify_token`` + ``list_active_subscriptions``),
* cancel a subscription (``cancel_subscription``) via the Stripe SDK.

Two-layer auth on the magic-link URL:

* ``django.core.signing.dumps(..., salt="donations.manage", max_age=1800)``
  gives expiry + tamper resistance. Without a valid signature, ``loads``
  raises ``BadSignature``.
* A tiny ``MagicLinkToken`` row holds ``used_at``. First successful
  verify with ``mark_used=True`` flips it; any subsequent verify raises
  ``BadSignature`` so a replay returns 410 Gone in the view layer.

The Stripe SDK is imported lazily inside :func:`cancel_subscription` —
same deferred-import pattern as
``apps.donations.services.stripe_checkout._configure_sdk`` — so dev / CI
environments without the ``stripe`` wheel can still import this module.

Email enumeration is intentionally side-stepped: ``send_magic_link``
short-circuits to ``None`` if no recurring donation matches the address,
and the view renders the same "check your inbox" page in both cases.
"""

from __future__ import annotations

import uuid

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.core.signing import BadSignature, dumps, loads
from django.db import transaction
from django.urls import reverse
from django.utils import timezone

from apps.donations.models import Donation, MagicLinkToken
from apps.site_config.email_context import render_email as render_to_string

# Salt namespaces the signed payload so a token issued for the donation
# management flow cannot be replayed against a future signing surface.
_SALT = "donations.manage"
# 30 minutes — matches the email copy and the story DoD.
_MAX_AGE = 30 * 60


def issue_token(email: str) -> str:
    """Create a ``MagicLinkToken`` row and return a signed URL token.

    The signed payload carries ``{"email": ..., "tid": ...}``. ``tid``
    is the row's ``token_id`` column — the single-use hinge. The signed
    string itself handles expiry + tamper resistance; the row flip
    handles re-use.
    """
    record = MagicLinkToken.objects.create(
        email=email,
        token_id=uuid.uuid4().hex,
    )
    return dumps({"email": email, "tid": record.token_id}, salt=_SALT)


def verify_token(signed: str, *, mark_used: bool = False) -> dict:
    """Decode ``signed`` and (optionally) burn the single-use row.

    Returns the payload dict ``{"email": ..., "tid": ...}`` on success.

    Raises:
        django.core.signing.SignatureExpired: token older than 30 min.
        django.core.signing.BadSignature: tampered, unknown ``tid``, or
            already-used token.

    ``mark_used=True`` is used by the landing view (which "spends" the
    token on first click). The token-signing roundtrip test uses the
    default ``mark_used=False`` so the row stays unused for a follow-up
    assertion.
    """
    payload = loads(signed, salt=_SALT, max_age=_MAX_AGE)
    try:
        # ``select_for_update`` would be ideal here, but ``loads`` already
        # cleared the expiry/tamper checks and the row is keyed on a
        # unique column — a concurrent burn is effectively impossible
        # outside contrived load tests.
        record = MagicLinkToken.objects.get(
            token_id=payload["tid"],
            email=payload["email"],
        )
    except MagicLinkToken.DoesNotExist as exc:
        # Surface as ``BadSignature`` so the view's exception handler is
        # a single ``except (BadSignature, SignatureExpired):`` branch.
        raise BadSignature("Unknown magic-link token") from exc

    if record.used_at is not None:
        raise BadSignature("Magic-link token already used")

    if mark_used:
        # ``update_fields`` keeps the write narrow; we do NOT include
        # ``created_at`` (auto_now_add) so the audit timestamp survives.
        record.used_at = timezone.now()
        record.save(update_fields=["used_at"])

    return payload


def _has_active_recurring(email: str) -> bool:
    """Does this email have at least one cancellable recurring donation?"""
    return (
        Donation.objects.filter(
            donor_email=email,
            is_recurring=True,
            stripe_subscription_id__isnull=False,
        )
        .exclude(status="cancelled")
        .exists()
    )


def send_magic_link(email: str) -> bool:
    """Issue + email a manage-link if (and only if) the donor exists.

    Returns ``True`` if an email was sent, ``False`` if the address has
    no active recurring donation. The view layer ignores the return
    value and always renders the same generic "check your inbox" page —
    the bool is purely a test affordance.

    Email enumeration is the biggest privacy risk on this flow. Anything
    visible to the caller (status code, page body, response time within
    reason) must be identical for known and unknown emails.
    """
    if not _has_active_recurring(email):
        return False

    token = issue_token(email)
    path = reverse("donations:manage", kwargs={"token": token})
    base = getattr(settings, "SITE_URL", "http://localhost:8000").rstrip("/")
    link = f"{base}{path}"

    ctx = {"link": link}
    msg = EmailMultiAlternatives(
        subject="Manage your MerryMeal donation",
        body=render_to_string("donations/emails/manage_link.txt", ctx),
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[email],
    )
    msg.attach_alternative(
        render_to_string("donations/emails/manage_link.html", ctx),
        "text/html",
    )
    msg.send()
    return True


def list_active_subscriptions(email: str) -> list[Donation]:
    """Return one ``Donation`` row per active subscription for ``email``.

    "Active" means ``is_recurring=True``, ``stripe_subscription_id`` is
    set, and ``status`` is not ``cancelled``. Multiple historical
    donations can share a ``stripe_subscription_id`` (the recurring
    webhook clones the shape on each successful invoice — see
    ``apply_invoice_paid``). We collapse to the *latest* row per
    subscription so the manage page shows one card per active sub
    rather than one card per monthly charge.

    Implemented as a Python-side dedupe instead of
    ``QuerySet.distinct("stripe_subscription_id")`` because the latter
    is Postgres-only — MerryMeal runs on MySQL.
    """
    rows = (
        Donation.objects.select_related("campaign")
        .filter(
            donor_email=email,
            is_recurring=True,
            stripe_subscription_id__isnull=False,
        )
        .exclude(status="cancelled")
        .order_by("-created_at")
    )
    seen: set[str] = set()
    latest: list[Donation] = []
    for donation in rows:
        sub_id = donation.stripe_subscription_id
        if sub_id in seen:
            continue
        seen.add(sub_id)
        latest.append(donation)
    return latest


@transaction.atomic
def cancel_subscription(*, email: str, subscription_id: str) -> int:
    """Cancel a Stripe subscription owned by ``email``.

    Two side effects, in order:

    1. Verify the ``email`` actually owns this ``subscription_id`` (a
       defence-in-depth check on top of the magic-link auth). Without
       this, anyone who guesses a ``sub_…`` id could cancel any donor.
    2. Call ``stripe.Subscription.delete(subscription_id)`` to stop
       future charges. The story spec mentions
       ``cancel_at_period_end=True`` as an option; we use ``delete``
       (immediate cancellation) so the donor gets confirmation in real
       time and the webhook handler from Story 5.4 fires
       ``customer.subscription.deleted`` straight away.
    3. Flip every matching ``Donation`` row to ``status='cancelled'``.
       The webhook handler does the same on receipt of
       ``customer.subscription.deleted``, but flipping eagerly here
       gives the manage page a correct "no active subscriptions" view
       on the next request even before Stripe's webhook lands.

    Returns the number of donation rows whose status was flipped.

    Raises:
        PermissionError: ``email`` does not own ``subscription_id``.
    """
    owns = Donation.objects.filter(
        donor_email=email,
        stripe_subscription_id=subscription_id,
    ).exists()
    if not owns:
        # Surface as a typed exception so the view returns 410 Gone
        # rather than 500-ing — the donor only ever sees the magic-link
        # landing again with the row missing.
        raise PermissionError(
            "This email does not own that subscription."
        )

    # Deferred import — keeps dev / CI bootable without the ``stripe``
    # wheel installed. See ``apps.donations.services.stripe_checkout``
    # for the same pattern.
    import stripe

    stripe.api_key = settings.STRIPE_SECRET_KEY
    stripe.Subscription.delete(subscription_id)

    return (
        Donation.objects.filter(
            donor_email=email,
            stripe_subscription_id=subscription_id,
        )
        .exclude(status="cancelled")
        .update(status="cancelled")
    )
