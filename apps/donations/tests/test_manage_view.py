"""Story 5.7 — end-to-end tests for the recurring-donation manage flow.

What's covered:

* ``GET /donate/manage/`` renders the email form.
* ``POST /donate/manage/`` with a known recurring-donor email sends the
  magic-link email and redirects to the "check your inbox" page.
* ``POST /donate/manage/`` with an unknown email silently succeeds
  (no email sent, identical redirect — privacy: no enumeration).
* ``GET /donate/manage/<valid-token>/`` renders the active-subscriptions
  list and burns the token.
* ``GET /donate/manage/<expired-token>/`` returns 410.
* ``GET /donate/manage/<used-token>/`` returns 410 (single-use).
* ``POST /donate/manage/<valid-token>/`` calls ``stripe.Subscription.delete``
  with the right subscription id and flips ``Donation.status`` to
  ``cancelled``.

The Stripe SDK is mocked via the stub installed in ``conftest.py`` —
the test patches ``stripe.Subscription.delete`` directly and asserts
the call signature.
"""

from __future__ import annotations

import re
import time as _time
from unittest.mock import patch

import pytest
from django.core import mail
from django.urls import reverse

from apps.donations.models import Donation, MagicLinkToken
from apps.donations.services.manage import issue_token
from apps.donations.tests.factories import CampaignFactory


def _make_recurring_donation(
    email: str = "donor@example.com",
    subscription_id: str = "sub_test_X",
    amount_cents: int = 2000,
) -> Donation:
    """Create one completed, recurring donation for the manage tests.

    The flow only cares about ``donor_email``, ``is_recurring``,
    ``stripe_subscription_id`` and ``status`` — but the model needs a
    full row (campaign + amount + payment type) to save.
    """
    campaign = CampaignFactory()
    return Donation.objects.create(
        campaign=campaign,
        donor_email=email,
        amount_cents=amount_cents,
        payment_type="card",
        status="completed",
        is_recurring=True,
        stripe_subscription_id=subscription_id,
    )


def _extract_token_from_email() -> str:
    """Pull the magic-link token out of the most recent outbox message."""
    body = mail.outbox[-1].body
    match = re.search(r"/donate/manage/(?P<tok>[^/\s]+)/", body)
    assert match is not None, f"No magic link found in email body: {body!r}"
    return match.group("tok")


# ----------------------------------------------------------------------
# Request form (GET + POST)
# ----------------------------------------------------------------------


@pytest.mark.django_db
def test_manage_request_get_renders_form(client):
    resp = client.get(reverse("donations:manage_request"))
    assert resp.status_code == 200
    # The email input + the "Send link" CTA should both be present.
    assert b'name="email"' in resp.content
    assert b"Send link" in resp.content


@pytest.mark.django_db
def test_manage_request_post_known_email_sends_link(client):
    _make_recurring_donation(email="known@example.com")
    resp = client.post(
        reverse("donations:manage_request"),
        {"email": "known@example.com"},
    )
    # Redirect to the "check your inbox" success page.
    assert resp.status_code == 302
    assert resp.url == reverse("donations:manage_request_sent")
    # An email was sent with a manage link.
    assert len(mail.outbox) == 1
    assert "donate/manage/" in mail.outbox[0].body


@pytest.mark.django_db
def test_manage_request_post_unknown_email_is_silent(client):
    # No recurring donations on file at all — the POST must still
    # respond identically to the known-email case (same redirect, no
    # error) to avoid email enumeration.
    resp = client.post(
        reverse("donations:manage_request"),
        {"email": "ghost@example.com"},
    )
    assert resp.status_code == 302
    assert resp.url == reverse("donations:manage_request_sent")
    # No outbox traffic — silent.
    assert len(mail.outbox) == 0


@pytest.mark.django_db
def test_manage_request_post_cancelled_subscription_treated_as_unknown(client):
    """A donor whose subscription is already ``cancelled`` no longer
    gets a magic link — the cancellation removed them from the
    "active recurring" set the manage flow targets.
    """
    donation = _make_recurring_donation(email="ex@example.com")
    donation.status = "cancelled"
    donation.save(update_fields=["status", "updated_at"])
    client.post(
        reverse("donations:manage_request"),
        {"email": "ex@example.com"},
    )
    assert len(mail.outbox) == 0


@pytest.mark.django_db
def test_manage_request_post_invalid_email_re_renders_form(client):
    resp = client.post(
        reverse("donations:manage_request"),
        {"email": "not-an-email"},
    )
    # Re-render (200), not a redirect — the malformed input is the
    # donor's mistake and the form should let them fix it.
    assert resp.status_code == 200
    assert b"Send link" in resp.content
    assert len(mail.outbox) == 0


@pytest.mark.django_db
def test_manage_request_sent_page_is_get_only(client):
    resp = client.get(reverse("donations:manage_request_sent"))
    assert resp.status_code == 200
    assert b"Check your inbox" in resp.content


# ----------------------------------------------------------------------
# Magic-link landing (GET)
# ----------------------------------------------------------------------


@pytest.mark.django_db
def test_manage_landing_lists_active_subscriptions(client):
    donation = _make_recurring_donation(
        email="donor@example.com",
        subscription_id="sub_active_1",
        amount_cents=2500,
    )
    token = issue_token("donor@example.com")
    resp = client.get(
        reverse("donations:manage", kwargs={"token": token})
    )
    assert resp.status_code == 200
    # Subscription id is rendered into the cancel form.
    assert b"sub_active_1" in resp.content
    # Amount is formatted as dollars.
    assert b"$25.00" in resp.content
    # Campaign name from the factory makes it onto the card.
    assert donation.campaign.name.encode() in resp.content


@pytest.mark.django_db
def test_manage_landing_burns_token_on_first_get(client):
    _make_recurring_donation()
    token = issue_token("donor@example.com")
    url = reverse("donations:manage", kwargs={"token": token})

    # First load is fine.
    first = client.get(url)
    assert first.status_code == 200
    # Token row should now be marked used.
    assert MagicLinkToken.objects.filter(used_at__isnull=False).count() == 1

    # Second load is 410.
    second = client.get(url)
    assert second.status_code == 410
    assert b"expired" in second.content.lower()


@pytest.mark.django_db
def test_manage_landing_expired_token_returns_410(client, monkeypatch):
    _make_recurring_donation()
    token = issue_token("donor@example.com")

    # Advance the signing module's clock 31 minutes — same idiom as
    # ``test_token_signing.test_token_expires_after_30_minutes``.
    from django.core import signing as _signing

    fake_now = _time.time() + 31 * 60
    monkeypatch.setattr(_signing.time, "time", lambda: fake_now)

    resp = client.get(reverse("donations:manage", kwargs={"token": token}))
    assert resp.status_code == 410


@pytest.mark.django_db
def test_manage_landing_tampered_token_returns_410(client):
    _make_recurring_donation()
    token = issue_token("donor@example.com")
    resp = client.get(
        reverse("donations:manage", kwargs={"token": token + "junk"})
    )
    assert resp.status_code == 410


@pytest.mark.django_db
def test_manage_landing_empty_when_no_active_subscriptions(client):
    """A donor with only cancelled subscriptions still lands cleanly —
    the page renders an empty-state message rather than crashing.
    """
    donation = _make_recurring_donation()
    donation.status = "cancelled"
    donation.save(update_fields=["status", "updated_at"])

    token = issue_token("donor@example.com")
    resp = client.get(reverse("donations:manage", kwargs={"token": token}))
    assert resp.status_code == 200
    assert b"no active recurring donations" in resp.content.lower()


# ----------------------------------------------------------------------
# Cancel POST
# ----------------------------------------------------------------------


@pytest.mark.django_db
def test_manage_cancel_calls_stripe_and_flips_status(client):
    donation = _make_recurring_donation(
        email="donor@example.com",
        subscription_id="sub_to_cancel",
    )
    token = issue_token("donor@example.com")
    url = reverse("donations:manage", kwargs={"token": token})

    # Burn the token (the cancel POST happens *after* the GET that
    # rendered the form — same as a real browser flow).
    client.get(url)

    with patch("stripe.Subscription.delete") as stripe_delete:
        resp = client.post(url, {"subscription_id": "sub_to_cancel"})

    # Stripe SDK was called with the right subscription id.
    stripe_delete.assert_called_once_with("sub_to_cancel")

    # The view re-renders the manage page with the success banner.
    assert resp.status_code == 200
    assert b"Subscription cancelled" in resp.content

    # Donation row is now ``cancelled``.
    donation.refresh_from_db()
    assert donation.status == "cancelled"


@pytest.mark.django_db
def test_manage_cancel_rejects_wrong_subscription_id(client):
    """A donor cannot cancel a subscription that belongs to another email.

    The magic-link auth restricts which email's subs are listed, but
    the cancel POST also runs a server-side ownership check so a
    crafted POST (subscription id swapped) returns 410 rather than
    cancelling someone else's gift.
    """
    _make_recurring_donation(
        email="donor@example.com", subscription_id="sub_owned"
    )
    _make_recurring_donation(
        email="someone-else@example.com", subscription_id="sub_other"
    )

    token = issue_token("donor@example.com")
    url = reverse("donations:manage", kwargs={"token": token})
    client.get(url)

    with patch("stripe.Subscription.delete") as stripe_delete:
        resp = client.post(url, {"subscription_id": "sub_other"})

    # Stripe SDK was NOT called — the ownership check tripped first.
    stripe_delete.assert_not_called()
    assert resp.status_code == 410

    # The other donor's subscription stays active.
    other = Donation.objects.get(stripe_subscription_id="sub_other")
    assert other.status == "completed"


@pytest.mark.django_db
def test_manage_cancel_expired_token_returns_410(client, monkeypatch):
    _make_recurring_donation()
    token = issue_token("donor@example.com")
    url = reverse("donations:manage", kwargs={"token": token})

    from django.core import signing as _signing

    fake_now = _time.time() + 31 * 60
    monkeypatch.setattr(_signing.time, "time", lambda: fake_now)

    with patch("stripe.Subscription.delete") as stripe_delete:
        resp = client.post(url, {"subscription_id": "sub_test_X"})

    stripe_delete.assert_not_called()
    assert resp.status_code == 410
