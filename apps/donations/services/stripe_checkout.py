"""Story 5.4 — Stripe Checkout session creation.

Wraps ``stripe.checkout.Session.create`` so the view layer (Story 5.3)
just calls ``create_checkout_session(donation_id, recurring)`` and gets
back a redirect URL. Side effects belong here, not on the model —
matches the MerryMeal layout rule from CLAUDE.md (services own side
effects; models are schema-only).

The module name is ``stripe_checkout`` and not ``stripe`` to avoid any
chance of an ``import stripe`` inside this file resolving back to itself
(or surprising a future reader). The story spec named it
``services/stripe.py``; the rename is a small, defensible deviation
flagged in the Story 5.4 commit body.

The ``import stripe`` is **deferred** to call-time, mirroring
``apps.core.services.sms_backends.TwilioBackend.send``. This lets dev /
CI environments without the ``stripe`` wheel still import the donations
app's module graph (tests install a sys.modules stub — see
``apps/donations/tests/conftest.py``).
"""

from __future__ import annotations

from django.conf import settings

from apps.donations.models import Donation


def _configure_sdk() -> object:
    """Import the Stripe SDK lazily and configure the API key.

    Returns the SDK module so callers can use it without a second import.
    """
    import stripe  # deferred — see module docstring

    stripe.api_key = settings.STRIPE_SECRET_KEY
    return stripe


def _absolute(path: str) -> str:
    """Stripe requires absolute redirect URLs.

    Resolve relative paths against ``settings.SITE_URL`` (already used
    for outbound email links). Falls back to ``http://localhost:8000``
    so a missing setting raises a Stripe API error rather than a
    ``KeyError`` deep in the SDK.
    """
    base = getattr(settings, "SITE_URL", "http://localhost:8000")
    if path.startswith("http://") or path.startswith("https://"):
        return path
    return base.rstrip("/") + path


def create_checkout_session(donation_id: int, recurring: bool) -> str:
    """Create a Stripe Checkout session and return its redirect URL.

    Args:
        donation_id: PK of the pending ``Donation`` row.
        recurring: ``True`` for a monthly subscription, ``False`` for a
            one-time gift.

    Returns:
        The fully-qualified ``checkout.stripe.com`` URL the donor's
        browser should be redirected to.

    Raises:
        TypeError: If ``amount_cents`` is not an ``int``. Stripe APIs
            speak integer cents; a float here means someone leaked
            dollars-as-float through Story 5.3's form. Better to fail
            loudly than charge $50.0 → 50 cents.
        Donation.DoesNotExist: If ``donation_id`` is unknown.
    """
    stripe = _configure_sdk()

    donation = Donation.objects.select_related("campaign").get(pk=donation_id)
    # Bool is a subclass of int in Python — reject explicitly so a stray
    # ``True`` doesn't get charged as 1 cent. ``isinstance(..., int) and
    # not isinstance(..., bool)`` is the canonical idiom here.
    if not isinstance(donation.amount_cents, int) or isinstance(
        donation.amount_cents, bool
    ):
        raise TypeError(
            "amount_cents must be int (integer cents); "
            f"got {type(donation.amount_cents).__name__}"
        )

    line_item: dict = {
        "price_data": {
            "currency": settings.DONATIONS_CURRENCY,
            "product_data": {
                "name": f"Donation — {donation.campaign.name}",
            },
            "unit_amount": donation.amount_cents,
        },
        "quantity": 1,
    }
    if recurring:
        line_item["price_data"]["recurring"] = {"interval": "month"}

    kwargs: dict = {
        "mode": "subscription" if recurring else "payment",
        "line_items": [line_item],
        "success_url": _absolute(settings.DONATIONS_SUCCESS_URL),
        "cancel_url": _absolute(settings.DONATIONS_CANCEL_URL),
        "customer_email": donation.donor_email,
        "metadata": {"donation_id": str(donation.id)},
    }
    if recurring:
        # Pass ``donation_id`` through to the subscription itself so the
        # ``customer.subscription.deleted`` event (Story 5.7) can link
        # back without an additional lookup.
        kwargs["subscription_data"] = {
            "metadata": {"donation_id": str(donation.id)},
        }

    session = stripe.checkout.Session.create(**kwargs)
    return session.url
