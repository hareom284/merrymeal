"""Tests for Story 4.12 — Member tracking page ("is it on the way?").

Covers:
* `apps.delivery.services.tracking.get_tracking_context` — status → label,
  volunteer display ("Sarah K."), `polling` flag toggling off for terminal
  states (`delivered`, `failed`).
* `GET /volunteer/member/delivery/<id>/status/` — auth, 404 for non-owners,
  partial body contents (`hx-trigger` present for live states, omitted for
  terminal states), green pill on delivered.

Adaptations from the spec
-------------------------
* `User` has no `first_name` / `last_name` — the model is `full_name`
  (see ``apps/accounts/models/users.py``). The service derives "Sarah K."
  from ``full_name.split()`` — the same pattern Story 4.8 already uses.
  Tests therefore set ``full_name="Sarah Khan"`` instead of
  ``first_name="Sarah", last_name="Khan"``.
* `pytest-freezer` is not installed; tests that need a stable time use
  ``timezone.now()`` directly without freezing — the assertions only
  check that ``delivered_at`` is not None, not its specific value.
"""
from __future__ import annotations

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.accounts.tests.factories import MemberCaregiverLinkFactory, UserFactory
from apps.delivery.tests.factories import DeliveryFactory


@pytest.mark.django_db
def test_tracking_context_pending():
    from apps.delivery.services.tracking import get_tracking_context

    d = DeliveryFactory(status="pending")
    ctx = get_tracking_context(d, d.member)

    assert ctx["status"] == "pending"
    assert ctx["polling"] is True
    assert "label" in ctx


@pytest.mark.django_db
def test_tracking_context_out_for_delivery_shows_volunteer_name():
    from apps.delivery.services.tracking import get_tracking_context

    vol = UserFactory(role="volunteer", full_name="Sarah Khan")
    d = DeliveryFactory(status="out_for_delivery", volunteer=vol)
    ctx = get_tracking_context(d, d.member)

    assert ctx["volunteer_display"] == "Sarah K."
    assert ctx["polling"] is True
    assert "Sarah K." in ctx["label"]


@pytest.mark.django_db
def test_tracking_context_volunteer_single_name_no_stray_period():
    """`full_name="Cher"` → "Cher", not "Cher .".

    Pitfall the reviewer explicitly calls out — guard against rendering
    a stray period when the last-name segment is empty.
    """
    from apps.delivery.services.tracking import get_tracking_context

    vol = UserFactory(role="volunteer", full_name="Cher")
    d = DeliveryFactory(status="out_for_delivery", volunteer=vol)
    ctx = get_tracking_context(d, d.member)

    assert ctx["volunteer_display"] == "Cher"
    assert "." not in ctx["volunteer_display"]


@pytest.mark.django_db
def test_tracking_context_delivered_stops_polling():
    from apps.delivery.services.tracking import get_tracking_context

    d = DeliveryFactory(status="delivered", delivered_time=timezone.now())
    ctx = get_tracking_context(d, d.member)

    assert ctx["status"] == "delivered"
    assert ctx["polling"] is False
    assert ctx["delivered_at"] is not None


@pytest.mark.django_db
def test_tracking_context_failed_stops_polling():
    from apps.delivery.services.tracking import get_tracking_context

    d = DeliveryFactory(status="failed")
    ctx = get_tracking_context(d, d.member)

    assert ctx["polling"] is False


@pytest.mark.django_db
def test_view_requires_login(client):
    d = DeliveryFactory()
    resp = client.get(reverse("delivery:tracking_status", args=[d.id]))
    # `@login_required` redirects unauthenticated requests.
    assert resp.status_code in (302, 401, 403)


@pytest.mark.django_db
def test_view_404_for_other_member(client):
    owner = UserFactory(role="member")
    intruder = UserFactory(role="member")
    d = DeliveryFactory(member=owner)

    client.force_login(intruder)
    resp = client.get(reverse("delivery:tracking_status", args=[d.id]))
    assert resp.status_code == 404


@pytest.mark.django_db
def test_view_404_for_unrelated_caregiver(client):
    """Caregivers linked to a different member must not see this member."""
    owner = UserFactory(role="member")
    other_member = UserFactory(role="member")
    stranger_caregiver = UserFactory(role="caregiver")
    MemberCaregiverLinkFactory(member=other_member, caregiver=stranger_caregiver)
    d = DeliveryFactory(member=owner)

    client.force_login(stranger_caregiver)
    resp = client.get(reverse("delivery:tracking_status", args=[d.id]))
    assert resp.status_code == 404


@pytest.mark.django_db
def test_view_allows_linked_caregiver(client):
    owner = UserFactory(role="member")
    caregiver = UserFactory(role="caregiver")
    MemberCaregiverLinkFactory(member=owner, caregiver=caregiver)
    d = DeliveryFactory(member=owner, status="pending")

    client.force_login(caregiver)
    resp = client.get(reverse("delivery:tracking_status", args=[d.id]))
    assert resp.status_code == 200


@pytest.mark.django_db
def test_view_renders_no_hx_trigger_when_terminal(client):
    member = UserFactory(role="member")
    d = DeliveryFactory(
        member=member, status="delivered", delivered_time=timezone.now()
    )

    client.force_login(member)
    resp = client.get(reverse("delivery:tracking_status", args=[d.id]))
    assert resp.status_code == 200
    assert b"hx-trigger" not in resp.content
    assert b"Delivered" in resp.content


@pytest.mark.django_db
def test_view_renders_hx_trigger_when_pending(client):
    member = UserFactory(role="member")
    d = DeliveryFactory(member=member, status="pending")

    client.force_login(member)
    resp = client.get(reverse("delivery:tracking_status", args=[d.id]))
    assert resp.status_code == 200
    assert b"hx-trigger" in resp.content
    assert b"every 60s" in resp.content


@pytest.mark.django_db
def test_view_renders_volunteer_display_for_out_for_delivery(client):
    member = UserFactory(role="member")
    vol = UserFactory(role="volunteer", full_name="Sarah Khan")
    d = DeliveryFactory(member=member, volunteer=vol, status="out_for_delivery")

    client.force_login(member)
    resp = client.get(reverse("delivery:tracking_status", args=[d.id]))
    assert resp.status_code == 200
    assert b"Sarah K." in resp.content
    assert b"hx-trigger" in resp.content


@pytest.mark.django_db
def test_view_renders_failed_pill(client):
    member = UserFactory(role="member")
    d = DeliveryFactory(member=member, status="failed")

    client.force_login(member)
    resp = client.get(reverse("delivery:tracking_status", args=[d.id]))
    assert resp.status_code == 200
    assert b"hx-trigger" not in resp.content
    # "Couldn't deliver" copy lives in the partial.
    assert b"deliver" in resp.content.lower()
