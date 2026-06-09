"""Gap P0-1 regression — ``start_donation`` must dispatch to the real
Stripe Checkout helper, not the legacy stub.

Story 5.3 originally imported a placeholder ``apps.donations.services.stripe``
module that returned a deterministic ``https://stripe.test/sess_stub_<id>``
URL so the public donate flow could be tested before Story 5.4 wired up the
real SDK call. Story 5.4 added ``apps.donations.services.stripe_checkout``
but never rewired ``apps.donations.services.donate`` to use it — donations
went out to a stub URL in production. These tests pin the fix so a future
refactor cannot silently regress to the stub again.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from apps.donations.models import Donation
from apps.donations.services import donate, stripe_checkout
from apps.donations.services.donate import start_donation
from apps.donations.tests.factories import CampaignFactory


def test_donate_module_uses_real_stripe_checkout_function():
    """``donate.create_checkout_session`` must be the real Stripe helper.

    Imports it as ``donate.create_checkout_session`` (the binding inside the
    donate module — that's what ``start_donation`` actually calls) and
    asserts identity with ``stripe_checkout.create_checkout_session``. If a
    future change reintroduces a stub, this assertion fails before any
    behavioural test runs.
    """
    assert donate.create_checkout_session is stripe_checkout.create_checkout_session


@pytest.mark.django_db
def test_start_donation_calls_real_helper_with_donation_id_and_recurring_flag():
    """``start_donation`` must hand the new ``donation.id`` to the helper.

    Patches the helper at the donate module's binding (patch where USED,
    not where it's defined) so the assertion exercises the same call site
    the production code path uses. The helper's return value must flow
    through to the URL returned by ``start_donation``.
    """
    CampaignFactory(slug="general-fund", name="General fund")
    expected_url = "https://checkout.stripe.com/c/pay/cs_test_wiring"
    with patch(
        "apps.donations.services.donate.create_checkout_session",
        return_value=expected_url,
    ) as mock_create:
        donation, url = start_donation(
            campaign_slug=None,
            amount_cents=5_000,
            donor_email="donor@example.com",
            is_recurring=False,
        )

    assert isinstance(donation, Donation)
    assert url == expected_url
    mock_create.assert_called_once_with(donation.id, recurring=False)


@pytest.mark.django_db
def test_start_donation_passes_recurring_true_through_to_helper():
    """Recurring gifts must reach the helper with ``recurring=True``.

    The helper switches to ``mode='subscription'`` on this flag — losing it
    here would silently downgrade a monthly subscription to a one-off
    charge, which would not be caught by the URL-shape assertion alone.
    """
    CampaignFactory(slug="general-fund", name="General fund")
    with patch(
        "apps.donations.services.donate.create_checkout_session",
        return_value="https://checkout.stripe.com/c/pay/cs_test_sub",
    ) as mock_create:
        donation, _ = start_donation(
            campaign_slug=None,
            amount_cents=2_000,
            donor_email="monthly@example.com",
            is_recurring=True,
        )

    mock_create.assert_called_once_with(donation.id, recurring=True)
    assert donation.is_recurring is True
