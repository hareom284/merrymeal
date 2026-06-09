"""View tests for the public donate page (Story 5.3).

Covers:

* GET ``/donate/`` renders without a campaign slug → general-fund hero.
* GET ``/donate/?campaign=<slug>`` renders the named campaign.
* GET ``/donate/?cancelled=1`` renders the soft toast.
* POST ``/donate/start/`` with valid data creates one pending Donation and
  redirects to the Stripe Checkout URL.
* POST with invalid data re-renders the form and creates no Donation.
* POST with ``is_recurring=on`` flips the model flag.

The Stripe Checkout call is patched at the donate service's use site
(``apps.donations.services.donate.create_checkout_session``) — patch where
it's used, not where it's defined — so the real ``stripe_checkout`` module
stays out of the test network path.
"""

from unittest.mock import patch

import pytest
from django.urls import reverse

from apps.donations.models import Donation
from apps.donations.tests.factories import CampaignFactory

FAKE_CHECKOUT_URL = "https://checkout.stripe.com/c/pay/cs_test_fake"


@pytest.fixture
def patched_checkout():
    """Replace the Stripe session helper used by ``start_donation``.

    The donate service imports ``create_checkout_session`` at module load,
    so the patch target is the donate module's binding (not
    ``stripe_checkout``'s). Returns the mock so individual tests can
    inspect call args if they need to.
    """
    with patch(
        "apps.donations.services.donate.create_checkout_session",
        return_value=FAKE_CHECKOUT_URL,
    ) as mock:
        yield mock


@pytest.mark.django_db
def test_donate_page_get_shows_general_fund_when_no_campaign(client):
    CampaignFactory(slug="general-fund", name="General fund")
    resp = client.get(reverse("donations:donate"))
    assert resp.status_code == 200
    assert b"General fund" in resp.content


@pytest.mark.django_db
def test_donate_page_get_shows_named_campaign(client):
    CampaignFactory(slug="general-fund", name="General fund")
    CampaignFactory(
        slug="winter-appeal",
        name="Winter appeal 2026",
        goal_cents=10_000_00,
    )
    resp = client.get(reverse("donations:donate") + "?campaign=winter-appeal")
    assert resp.status_code == 200
    assert b"Winter appeal 2026" in resp.content


@pytest.mark.django_db
def test_donate_page_get_shows_cancelled_toast(client):
    CampaignFactory(slug="general-fund", name="General fund")
    resp = client.get(reverse("donations:donate") + "?cancelled=1")
    assert resp.status_code == 200
    assert b"Cancelled" in resp.content


@pytest.mark.django_db
def test_donate_page_get_unknown_campaign_falls_back_to_general_fund(client):
    CampaignFactory(slug="general-fund", name="General fund")
    resp = client.get(reverse("donations:donate") + "?campaign=does-not-exist")
    assert resp.status_code == 200
    assert b"General fund" in resp.content


@pytest.mark.django_db
def test_donate_start_creates_pending_donation_and_redirects(
    client, patched_checkout
):
    CampaignFactory(slug="general-fund", name="General fund")
    resp = client.post(
        reverse("donations:donate_start"),
        {
            "amount_dollars": "50",
            "donor_email": "donor@example.com",
            "is_recurring": "",
            "campaign_slug": "",
        },
    )
    assert resp.status_code == 302
    assert resp["Location"] == FAKE_CHECKOUT_URL
    d = Donation.objects.get()
    assert d.amount_cents == 5000
    assert d.status == "pending"
    assert d.is_recurring is False
    assert d.donor_email == "donor@example.com"
    assert d.campaign.slug == "general-fund"
    assert d.payment_type == "card"
    patched_checkout.assert_called_once_with(d.id, recurring=False)


@pytest.mark.django_db
def test_donate_start_with_recurring_flag_creates_recurring_donation(
    client, patched_checkout
):
    CampaignFactory(slug="general-fund", name="General fund")
    resp = client.post(
        reverse("donations:donate_start"),
        {
            "amount_dollars": "20",
            "donor_email": "donor@example.com",
            "is_recurring": "on",
            "campaign_slug": "",
        },
    )
    assert resp.status_code == 302
    d = Donation.objects.get()
    assert d.is_recurring is True
    patched_checkout.assert_called_once_with(d.id, recurring=True)


@pytest.mark.django_db
def test_donate_start_resolves_named_campaign(client, patched_checkout):
    CampaignFactory(slug="general-fund", name="General fund")
    winter = CampaignFactory(slug="winter-appeal", name="Winter appeal 2026")
    resp = client.post(
        reverse("donations:donate_start"),
        {
            "amount_dollars": "100",
            "donor_email": "donor@example.com",
            "is_recurring": "",
            "campaign_slug": "winter-appeal",
        },
    )
    assert resp.status_code == 302
    d = Donation.objects.get()
    assert d.campaign_id == winter.id


@pytest.mark.django_db
def test_donate_start_unknown_slug_falls_back_to_general_fund(
    client, patched_checkout
):
    general = CampaignFactory(slug="general-fund", name="General fund")
    resp = client.post(
        reverse("donations:donate_start"),
        {
            "amount_dollars": "25",
            "donor_email": "donor@example.com",
            "is_recurring": "",
            "campaign_slug": "does-not-exist",
        },
    )
    assert resp.status_code == 302
    d = Donation.objects.get()
    assert d.campaign_id == general.id


@pytest.mark.django_db
def test_donate_start_invalid_form_rerenders_with_errors(client, patched_checkout):
    CampaignFactory(slug="general-fund", name="General fund")
    resp = client.post(
        reverse("donations:donate_start"),
        {
            "amount_dollars": "0",
            "donor_email": "x",
            "is_recurring": "",
        },
    )
    assert resp.status_code == 200  # form re-render
    assert Donation.objects.count() == 0
    # Invalid form must short-circuit before any Stripe interaction.
    patched_checkout.assert_not_called()


@pytest.mark.django_db
def test_donate_page_does_not_require_login(client):
    """No login redirect — public donations are the whole point of the page."""
    CampaignFactory(slug="general-fund", name="General fund")
    resp = client.get(reverse("donations:donate"))
    assert resp.status_code == 200
