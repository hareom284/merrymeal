"""Story 5.4 — webhook signature, status flip, and idempotency tests.

The webhook view calls ``stripe.Webhook.construct_event`` for signature
verification. Tests patch that function so:

* A test that simulates a *bad* signature has the patch raise
  ``stripe.error.SignatureVerificationError`` — the view must return
  **HTTP 401 with zero DB writes**.
* A test that simulates a *valid* signature has the patch return the
  decoded event dict — the view dispatches to the payment service.

Idempotency is the load-bearing assertion: re-firing the same
``checkout.session.completed`` event must NOT create a second Donation
row and must NOT double-count the campaign total. The hinge is the
``Donation.transaction_id`` unique column from Story 5.2.
"""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest
import stripe  # provided by the sys.modules stub in conftest
from django.urls import reverse

from apps.donations.models import Donation
from apps.donations.services.campaigns import raised_cents_for
from apps.donations.tests.factories import CampaignFactory

# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------

def _checkout_payload(donation_id: int, session_id: str = "cs_test_999") -> dict:
    return {
        "id": "evt_test_1",
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": session_id,
                "metadata": {"donation_id": str(donation_id)},
                "amount_total": 5_000,
                "currency": "aud",
                "mode": "payment",
            }
        },
    }


def _post(client, payload, sig="t=1,v1=valid"):
    return client.post(
        reverse("donations:stripe_webhook"),
        data=json.dumps(payload),
        content_type="application/json",
        HTTP_STRIPE_SIGNATURE=sig,
    )


# ----------------------------------------------------------------------
# Signature verification
# ----------------------------------------------------------------------

@pytest.mark.django_db
def test_webhook_rejects_bad_signature():
    """Forged signature → HTTP 401, no Donation row touched."""
    from django.test import Client

    client = Client()
    payload = {"id": "evt_x", "type": "checkout.session.completed"}
    before = Donation.objects.count()
    with patch(
        "stripe.Webhook.construct_event",
        side_effect=stripe.error.SignatureVerificationError(
            "bad sig", "t=1,v1=bogus"
        ),
    ):
        resp = _post(client, payload, sig="t=1,v1=bogus")
    assert resp.status_code == 401
    assert Donation.objects.count() == before


@pytest.mark.django_db
def test_webhook_rejects_missing_signature_header():
    """No ``Stripe-Signature`` header at all → 401."""
    from django.test import Client

    client = Client()
    payload = {"id": "evt_x", "type": "checkout.session.completed"}
    with patch(
        "stripe.Webhook.construct_event",
        side_effect=ValueError("missing sig"),
    ):
        resp = client.post(
            reverse("donations:stripe_webhook"),
            data=json.dumps(payload),
            content_type="application/json",
        )
    assert resp.status_code == 401


# ----------------------------------------------------------------------
# checkout.session.completed
# ----------------------------------------------------------------------

@pytest.mark.django_db
def test_webhook_marks_donation_completed(client):
    """Valid checkout event flips the pending Donation to completed."""
    campaign = CampaignFactory(slug="general-fund")
    donation = Donation.objects.create(
        campaign=campaign,
        donor_email="a@x.com",
        amount_cents=5_000,
        payment_type="card",
        status="pending",
    )
    payload = _checkout_payload(donation.id)
    with patch("stripe.Webhook.construct_event", return_value=payload):
        resp = _post(client, payload)

    assert resp.status_code == 200
    donation.refresh_from_db()
    assert donation.status == "completed"
    assert donation.transaction_id == "cs_test_999"


@pytest.mark.django_db
def test_webhook_is_idempotent_on_refire(client):
    """Re-firing the same event → exactly one row, total counted once.

    This is the production safety net Story 5.4 cares about most.
    Stripe re-fires events on network errors; without idempotency the
    campaign progress bar drifts. The ``Donation.transaction_id`` unique
    column + the upsert path in ``apply_checkout_completed`` together
    enforce this.
    """
    campaign = CampaignFactory(slug="general-fund")
    donation = Donation.objects.create(
        campaign=campaign,
        donor_email="a@x.com",
        amount_cents=5_000,
        payment_type="card",
        status="pending",
    )
    payload = _checkout_payload(donation.id)

    with patch("stripe.Webhook.construct_event", return_value=payload):
        first = _post(client, payload)
        second = _post(client, payload)  # same event ID

    assert first.status_code == 200
    assert second.status_code == 200
    # Exactly one Donation row exists.
    assert Donation.objects.count() == 1
    only = Donation.objects.get()
    assert only.status == "completed"
    assert only.transaction_id == "cs_test_999"
    # Campaign total reflects $50 once, not twice.
    assert raised_cents_for(campaign) == 5_000


@pytest.mark.django_db
def test_webhook_unknown_event_type_returns_200(client):
    """Unknown event type → 200 OK so Stripe stops retrying."""
    payload = {
        "id": "evt_unknown",
        "type": "charge.refunded",
        "data": {"object": {"id": "ch_test_1"}},
    }
    with patch("stripe.Webhook.construct_event", return_value=payload):
        resp = _post(client, payload)
    assert resp.status_code == 200


# ----------------------------------------------------------------------
# invoice.paid (recurring)
# ----------------------------------------------------------------------

@pytest.mark.django_db
def test_recurring_first_invoice_flips_pending(client):
    """First ``invoice.paid`` for a subscription → flip the pending row."""
    campaign = CampaignFactory(slug="general-fund")
    pending = Donation.objects.create(
        campaign=campaign,
        donor_email="a@x.com",
        amount_cents=2_000,
        payment_type="card",
        status="pending",
        is_recurring=True,
        stripe_subscription_id="sub_test_1",
    )
    payload = {
        "id": "evt_invoice_1",
        "type": "invoice.paid",
        "data": {
            "object": {
                "id": "in_first",
                "subscription": "sub_test_1",
                "amount_paid": 2_000,
                "currency": "aud",
                "customer_email": "a@x.com",
            }
        },
    }
    with patch("stripe.Webhook.construct_event", return_value=payload):
        resp = _post(client, payload)

    assert resp.status_code == 200
    pending.refresh_from_db()
    assert pending.status == "completed"
    assert pending.transaction_id == "in_first"
    assert Donation.objects.count() == 1


@pytest.mark.django_db
def test_recurring_second_invoice_creates_new_donation(client):
    """Subsequent ``invoice.paid`` → new row linked by subscription id."""
    campaign = CampaignFactory(slug="general-fund")
    Donation.objects.create(
        campaign=campaign,
        donor_email="a@x.com",
        amount_cents=2_000,
        payment_type="card",
        status="completed",
        is_recurring=True,
        stripe_subscription_id="sub_test_1",
        transaction_id="in_first",
    )
    payload = {
        "id": "evt_invoice_2",
        "type": "invoice.paid",
        "data": {
            "object": {
                "id": "in_second",
                "subscription": "sub_test_1",
                "amount_paid": 2_000,
                "currency": "aud",
                "customer_email": "a@x.com",
            }
        },
    }
    with patch("stripe.Webhook.construct_event", return_value=payload):
        resp = _post(client, payload)

    assert resp.status_code == 200
    assert (
        Donation.objects.filter(stripe_subscription_id="sub_test_1").count() == 2
    )
    second = Donation.objects.get(transaction_id="in_second")
    assert second.status == "completed"
    assert second.is_recurring is True
    assert second.campaign_id == campaign.id


@pytest.mark.django_db
def test_recurring_invoice_refire_is_idempotent(client):
    """Re-firing the same ``invoice.paid`` event → no duplicate row."""
    campaign = CampaignFactory(slug="general-fund")
    Donation.objects.create(
        campaign=campaign,
        donor_email="a@x.com",
        amount_cents=2_000,
        payment_type="card",
        status="completed",
        is_recurring=True,
        stripe_subscription_id="sub_test_1",
        transaction_id="in_first",
    )
    payload = {
        "id": "evt_invoice_2",
        "type": "invoice.paid",
        "data": {
            "object": {
                "id": "in_second",
                "subscription": "sub_test_1",
                "amount_paid": 2_000,
                "currency": "aud",
                "customer_email": "a@x.com",
            }
        },
    }
    with patch("stripe.Webhook.construct_event", return_value=payload):
        _post(client, payload)
        _post(client, payload)  # re-fire

    assert (
        Donation.objects.filter(stripe_subscription_id="sub_test_1").count() == 2
    )
    assert raised_cents_for(campaign) == 4_000  # not 6_000


# ----------------------------------------------------------------------
# customer.subscription.deleted (Story 5.7 hook)
# ----------------------------------------------------------------------

@pytest.mark.django_db
def test_subscription_deleted_marks_donations_cancelled(client):
    """``customer.subscription.deleted`` → flip donations to cancelled."""
    campaign = CampaignFactory(slug="general-fund")
    Donation.objects.create(
        campaign=campaign,
        donor_email="a@x.com",
        amount_cents=2_000,
        payment_type="card",
        status="completed",
        is_recurring=True,
        stripe_subscription_id="sub_test_99",
        transaction_id="in_only",
    )
    payload = {
        "id": "evt_sub_del",
        "type": "customer.subscription.deleted",
        "data": {"object": {"id": "sub_test_99"}},
    }
    with patch("stripe.Webhook.construct_event", return_value=payload):
        resp = _post(client, payload)

    assert resp.status_code == 200
    assert (
        Donation.objects
        .filter(stripe_subscription_id="sub_test_99")
        .values_list("status", flat=True)
        .first()
        == "cancelled"
    )
