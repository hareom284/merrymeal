"""Story 5.5 — receipt-email behaviour through the webhook surface.

Asserts the end-to-end contract: a ``checkout.session.completed`` event
flips the pending ``Donation`` AND sends exactly one receipt email with
the right shape (donor, dollars, campaign, receipt number, ATO ABN
line). A re-fired event must NOT send a second copy — the gate is
``donation.receipt_number`` being already set.

We patch ``stripe.Webhook.construct_event`` (the dev/CI stripe stub
lives in ``conftest._install_stripe_stub``) so the webhook view's
signature check returns the test payload verbatim. Email backend in
tests is ``locmem`` — Django's settings default flips to that when
``settings.EMAIL_BACKEND`` is unset under pytest-django, but we set it
explicitly via ``override_settings`` so a future contributor changing
``config/settings/test.py`` cannot silently break us.
"""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest
from django.core import mail
from django.test import override_settings
from django.urls import reverse

from apps.donations.models import Donation
from apps.donations.tests.factories import CampaignFactory


def _payload(donation_id: int, session_id: str = "cs_test_1") -> dict:
    return {
        "id": "evt_receipt_1",
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


def _post(client, payload):
    return client.post(
        reverse("donations:stripe_webhook"),
        data=json.dumps(payload),
        content_type="application/json",
        HTTP_STRIPE_SIGNATURE="t=1,v1=valid",
    )


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    DONATIONS_CHARITY_ABN="99 123 456 789",
    DONATIONS_CHARITY_ADDRESS="42 Test Lane, Melbourne VIC 3000",
    DONATIONS_FROM_EMAIL="receipts@merrymeal.test",
)
@pytest.mark.django_db
def test_receipt_email_sent_on_completion(client):
    mail.outbox.clear()
    campaign = CampaignFactory(slug="winter-appeal", name="Winter appeal")
    donation = Donation.objects.create(
        campaign=campaign,
        donor_email="alice@example.com",
        amount_cents=5_000,
        payment_type="card",
        status="pending",
    )
    payload = _payload(donation.id)
    with patch("stripe.Webhook.construct_event", return_value=payload):
        resp = _post(client, payload)

    assert resp.status_code == 200
    donation.refresh_from_db()
    assert donation.status == "completed"
    assert donation.receipt_number  # populated by the receipt service

    assert len(mail.outbox) == 1
    msg = mail.outbox[0]
    assert msg.to == ["alice@example.com"]
    assert msg.from_email == "receipts@merrymeal.test"
    assert donation.receipt_number in msg.subject

    # Plain-text body covers the load-bearing content.
    assert "$50.00" in msg.body
    assert "Winter appeal" in msg.body
    assert donation.receipt_number in msg.body
    assert "99 123 456 789" in msg.body
    assert "42 Test Lane" in msg.body

    # HTML alternative is attached and renders the same headline figure.
    assert len(msg.alternatives) == 1
    html_body, mime = msg.alternatives[0]
    assert mime == "text/html"
    assert "$50.00" in html_body
    assert "Winter appeal" in html_body
    assert donation.receipt_number in html_body


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
)
@pytest.mark.django_db
def test_refire_does_not_send_duplicate_email(client):
    """Stripe re-fires events on network errors — receipt must not double."""
    mail.outbox.clear()
    campaign = CampaignFactory(slug="general-fund", name="General fund")
    donation = Donation.objects.create(
        campaign=campaign,
        donor_email="alice@example.com",
        amount_cents=5_000,
        payment_type="card",
        status="pending",
    )
    payload = _payload(donation.id)

    with patch("stripe.Webhook.construct_event", return_value=payload):
        _post(client, payload)
        _post(client, payload)  # same session id — Stripe retry

    assert Donation.objects.count() == 1
    assert len(mail.outbox) == 1

    # Receipt number is stable across the re-fire — the row keeps its
    # original number, the second pass short-circuits.
    donation.refresh_from_db()
    first_number = donation.receipt_number
    assert first_number is not None
    # Sanity: re-running the gate by hand is a no-op too.
    from apps.donations.services.receipts import assign_receipt_number
    assert assign_receipt_number(donation) == first_number


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
)
@pytest.mark.django_db
def test_recurring_first_invoice_sends_one_receipt(client):
    """``invoice.paid`` (first invoice) also triggers exactly one receipt."""
    mail.outbox.clear()
    campaign = CampaignFactory(slug="general-fund", name="General fund")
    pending = Donation.objects.create(
        campaign=campaign,
        donor_email="recur@example.com",
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
                "customer_email": "recur@example.com",
            }
        },
    }
    with patch("stripe.Webhook.construct_event", return_value=payload):
        _post(client, payload)
        _post(client, payload)  # idempotency re-fire

    assert len(mail.outbox) == 1
    pending.refresh_from_db()
    assert pending.receipt_number is not None
    assert pending.receipt_number in mail.outbox[0].subject
