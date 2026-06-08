"""Story 5.4 — service-level tests for the Stripe Checkout helper.

Each test mocks ``stripe.checkout.Session.create`` so we never touch
Stripe's network. The ``stripe`` package itself is a sys.modules stub
installed by ``apps/donations/tests/conftest.py`` — MerryMeal dev / CI
does not pip-install the real SDK.

Mirrors the conventions in CLAUDE.md: services own side effects;
``amount_cents`` is integer cents (the float-rejection test is the
guard rail).
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from apps.donations.services.stripe_checkout import create_checkout_session
from apps.donations.tests.factories import DonationFactory


@pytest.mark.django_db
def test_one_time_session_uses_payment_mode(stripe_session_stub):
    """``recurring=False`` → ``mode="payment"`` + single AUD line item."""
    donation = DonationFactory(amount_cents=5_000, is_recurring=False)
    with patch(
        "stripe.checkout.Session.create",
        return_value=stripe_session_stub,
    ) as create:
        url = create_checkout_session(donation.id, recurring=False)

    _, kwargs = create.call_args
    assert kwargs["mode"] == "payment"
    line = kwargs["line_items"][0]
    assert line["price_data"]["unit_amount"] == 5_000
    assert line["price_data"]["currency"] == "aud"
    assert kwargs["metadata"]["donation_id"] == str(donation.id)
    # ``recurring`` key only added on subscription mode.
    assert "recurring" not in line["price_data"]
    assert url.startswith("https://checkout.stripe.com/")


@pytest.mark.django_db
def test_recurring_session_uses_subscription_mode(stripe_session_stub):
    """``recurring=True`` → ``mode="subscription"`` + monthly interval."""
    donation = DonationFactory(amount_cents=2_000, is_recurring=True)
    with patch(
        "stripe.checkout.Session.create",
        return_value=stripe_session_stub,
    ) as create:
        create_checkout_session(donation.id, recurring=True)

    _, kwargs = create.call_args
    assert kwargs["mode"] == "subscription"
    line = kwargs["line_items"][0]
    assert line["price_data"]["recurring"] == {"interval": "month"}
    assert line["price_data"]["unit_amount"] == 2_000
    # Subscription metadata still carries ``donation_id`` so
    # ``customer.subscription.deleted`` events can link back.
    sub_data = kwargs.get("subscription_data") or {}
    assert sub_data.get("metadata", {}).get("donation_id") == str(donation.id)


@pytest.mark.django_db
def test_success_and_cancel_urls_are_absolute(stripe_session_stub):
    """Stripe rejects relative redirect URLs — both must be absolute."""
    donation = DonationFactory()
    with patch(
        "stripe.checkout.Session.create",
        return_value=stripe_session_stub,
    ) as create:
        create_checkout_session(donation.id, recurring=False)

    _, kwargs = create.call_args
    assert kwargs["success_url"].startswith("http")
    assert "session_id={CHECKOUT_SESSION_ID}" in kwargs["success_url"]
    assert kwargs["cancel_url"].startswith("http")
    assert "cancelled=1" in kwargs["cancel_url"]


@pytest.mark.django_db
def test_rejects_non_integer_amount():
    """Float ``amount_cents`` is a bug — raise instead of charging $50.00.

    ``BigIntegerField`` coerces floats on save, so we patch the re-fetch
    to simulate the bug surfacing after a Story 5.3 form leaked dollars
    through as a float (e.g. a future ``DecimalField`` migration).
    """
    donation = DonationFactory()
    donation.amount_cents = 50.0  # bug: dollars-as-float in memory

    from apps.donations.services import stripe_checkout as service

    fake_qs = type(
        "_QS",
        (),
        {"get": staticmethod(lambda pk: donation)},
    )()
    with patch.object(
        service.Donation.objects, "select_related", return_value=fake_qs
    ):
        with pytest.raises(TypeError):
            create_checkout_session(donation.id, recurring=False)
