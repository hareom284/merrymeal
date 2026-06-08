"""Story 5.5 — thanks page view tests.

Two paths:

* **Happy path** — Stripe's redirect lands the donor on
  ``/donate/thanks/?session_id=<sid>`` after the webhook has already
  flipped the row to ``completed`` (Stripe usually wins this race by
  seconds). The page renders the amount, campaign, and receipt number.

* **Pending path** — the webhook hasn't arrived yet (or the session id
  isn't ours). The page renders a soft "processing" state with a
  refresh hint instead of 404ing on the donor.

The view is public (no auth) and GET-only.
"""

from __future__ import annotations

import pytest
from django.urls import reverse

from apps.donations.models import Donation
from apps.donations.tests.factories import CampaignFactory


@pytest.mark.django_db
def test_thanks_renders_completed_donation(client):
    campaign = CampaignFactory(name="Winter appeal", slug="winter-appeal")
    Donation.objects.create(
        campaign=campaign,
        donor_email="alice@example.com",
        amount_cents=5_000,
        payment_type="card",
        status="completed",
        transaction_id="cs_test_thanks_1",
        receipt_number="D2026-000042",
    )
    resp = client.get(
        reverse("donations:thanks") + "?session_id=cs_test_thanks_1"
    )
    assert resp.status_code == 200
    body = resp.content.decode()
    assert "$50.00" in body
    assert "Winter appeal" in body
    assert "D2026-000042" in body
    assert "alice@example.com" in body


@pytest.mark.django_db
def test_thanks_pending_session_renders_processing_state(client):
    resp = client.get(reverse("donations:thanks") + "?session_id=cs_unknown")
    assert resp.status_code == 200
    assert b"processing" in resp.content.lower()


@pytest.mark.django_db
def test_thanks_missing_session_id_renders_processing_state(client):
    """No ``?session_id=`` query string at all — same soft pending state."""
    resp = client.get(reverse("donations:thanks"))
    assert resp.status_code == 200
    assert b"processing" in resp.content.lower()


@pytest.mark.django_db
def test_thanks_pending_donation_renders_processing_state(client):
    """A row that exists but is still ``pending`` — webhook race; show soft state."""
    campaign = CampaignFactory()
    Donation.objects.create(
        campaign=campaign,
        donor_email="bob@example.com",
        amount_cents=2_000,
        payment_type="card",
        status="pending",
        transaction_id="cs_test_thanks_2",
    )
    resp = client.get(
        reverse("donations:thanks") + "?session_id=cs_test_thanks_2"
    )
    assert resp.status_code == 200
    assert b"processing" in resp.content.lower()


@pytest.mark.django_db
def test_thanks_renders_meal_count(client):
    """The donor sees the same "≈ N meals" caption as the impact preview."""
    campaign = CampaignFactory(name="General fund", slug="general-fund")
    Donation.objects.create(
        campaign=campaign,
        donor_email="alice@example.com",
        amount_cents=5_000,  # $50 / $3 per meal = 16 meals
        payment_type="card",
        status="completed",
        transaction_id="cs_test_thanks_3",
        receipt_number="D2026-000007",
    )
    resp = client.get(
        reverse("donations:thanks") + "?session_id=cs_test_thanks_3"
    )
    assert resp.status_code == 200
    # 5000 // 300 = 16
    assert b"16 meals" in resp.content
