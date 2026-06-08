"""Story 4.14 — Admin reassignment widget tests.

Covers:
    * The ``reassign_delivery`` service (volunteer/route updates, route
      creation for volunteers with no route today, the 12-stop cap,
      non-volunteer rejection, audit log emission).
    * The two HTTP endpoints (``admin_today`` list + ``admin_reassign``
      modal/POST), including the 403 gate for non-admin callers and
      the HX-Trigger response header used by the modal close handler.
"""
from __future__ import annotations

import datetime as dt

import pytest
from auditlog.models import LogEntry
from django.urls import reverse

from apps.accounts.tests.factories import UserFactory
from apps.delivery.models import Route
from apps.delivery.services.reassign import MAX_STOPS_PER_ROUTE, reassign_delivery
from apps.delivery.tests.factories import DeliveryFactory, RouteFactory

# ---------------------------------------------------------------------------
# Service tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_reassign_updates_volunteer_and_route():
    today = dt.date.today()
    old_route = RouteFactory(route_date=today)
    delivery = DeliveryFactory(
        route=old_route,
        volunteer=old_route.volunteer,
        scheduled_date=today,
    )
    new_vol = UserFactory(role="volunteer")
    new_route = RouteFactory(volunteer=new_vol, route_date=today)

    reassign_delivery(delivery, new_volunteer=new_vol)

    delivery.refresh_from_db()
    assert delivery.volunteer_id == new_vol.id
    assert delivery.route_id == new_route.id


@pytest.mark.django_db
def test_reassign_creates_route_when_new_volunteer_has_none():
    today = dt.date.today()
    delivery = DeliveryFactory(scheduled_date=today)
    new_vol = UserFactory(role="volunteer")
    assert not Route.objects.filter(volunteer=new_vol).exists()

    reassign_delivery(delivery, new_volunteer=new_vol)

    delivery.refresh_from_db()
    assert delivery.route_id is not None
    assert Route.objects.filter(volunteer=new_vol, route_date=today).exists()


@pytest.mark.django_db
def test_reassign_rejects_non_volunteer():
    delivery = DeliveryFactory()
    member = UserFactory(role="member")
    with pytest.raises(ValueError):
        reassign_delivery(delivery, new_volunteer=member)


@pytest.mark.django_db
def test_reassign_rejects_over_cap():
    today = dt.date.today()
    new_vol = UserFactory(role="volunteer")
    new_route = RouteFactory(volunteer=new_vol, route_date=today)
    DeliveryFactory.create_batch(
        MAX_STOPS_PER_ROUTE,
        route=new_route,
        volunteer=new_vol,
        scheduled_date=today,
    )
    delivery = DeliveryFactory(scheduled_date=today)

    with pytest.raises(ValueError):
        reassign_delivery(delivery, new_volunteer=new_vol)


@pytest.mark.django_db
def test_reassign_rejects_same_volunteer():
    """Reassigning to the existing volunteer is a no-op we reject loudly."""
    delivery = DeliveryFactory()
    same_vol = delivery.volunteer
    with pytest.raises(ValueError):
        reassign_delivery(delivery, new_volunteer=same_vol)


@pytest.mark.django_db
def test_reassign_writes_audit_log():
    delivery = DeliveryFactory()
    new_vol = UserFactory(role="volunteer")
    before = LogEntry.objects.filter(object_id=delivery.id).count()

    reassign_delivery(delivery, new_volunteer=new_vol)

    after = LogEntry.objects.filter(object_id=delivery.id).count()
    assert after > before


# ---------------------------------------------------------------------------
# View tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_admin_today_blocks_non_admin(client):
    vol = UserFactory(role="volunteer")
    client.force_login(vol)
    resp = client.get(reverse("delivery:admin_today"))
    assert resp.status_code == 403


@pytest.mark.django_db
def test_admin_today_lists_todays_deliveries(client):
    admin = UserFactory(role="admin")
    today = dt.date.today()
    yesterday = today - dt.timedelta(days=1)
    today_d = DeliveryFactory(scheduled_date=today)
    DeliveryFactory(scheduled_date=yesterday)  # must NOT appear

    client.force_login(admin)
    resp = client.get(reverse("delivery:admin_today"))
    assert resp.status_code == 200
    deliveries = list(resp.context["deliveries"])
    assert today_d in deliveries
    assert len(deliveries) == 1


@pytest.mark.django_db
def test_reassign_modal_get_renders_form(client):
    admin = UserFactory(role="admin")
    delivery = DeliveryFactory()
    client.force_login(admin)
    resp = client.get(reverse("delivery:admin_reassign", args=[delivery.pk]))
    assert resp.status_code == 200
    assert b"reassign-modal" in resp.content


@pytest.mark.django_db
def test_reassign_post_swaps_row_and_triggers_close(client):
    admin = UserFactory(role="admin")
    today = dt.date.today()
    delivery = DeliveryFactory(scheduled_date=today)
    new_vol = UserFactory(role="volunteer")

    client.force_login(admin)
    resp = client.post(
        reverse("delivery:admin_reassign", args=[delivery.pk]),
        {"volunteer": new_vol.pk},
    )
    assert resp.status_code == 200
    assert resp.headers.get("HX-Trigger") == "closeModal"

    delivery.refresh_from_db()
    assert delivery.volunteer_id == new_vol.id


@pytest.mark.django_db
def test_reassign_post_rejects_non_volunteer(client):
    admin = UserFactory(role="admin")
    delivery = DeliveryFactory()
    member = UserFactory(role="member")
    client.force_login(admin)
    resp = client.post(
        reverse("delivery:admin_reassign", args=[delivery.pk]),
        {"volunteer": member.pk},
    )
    # ModelChoiceField queryset excludes non-volunteers → form invalid → 400.
    assert resp.status_code == 400


@pytest.mark.django_db
def test_reassign_post_rejects_same_volunteer(client):
    admin = UserFactory(role="admin")
    delivery = DeliveryFactory()
    client.force_login(admin)
    resp = client.post(
        reverse("delivery:admin_reassign", args=[delivery.pk]),
        {"volunteer": delivery.volunteer_id},
    )
    assert resp.status_code == 400


@pytest.mark.django_db
def test_reassign_post_blocks_non_admin(client):
    vol = UserFactory(role="volunteer")
    delivery = DeliveryFactory()
    target_vol = UserFactory(role="volunteer")
    client.force_login(vol)
    resp = client.post(
        reverse("delivery:admin_reassign", args=[delivery.pk]),
        {"volunteer": target_vol.pk},
    )
    assert resp.status_code == 403
    delivery.refresh_from_db()
    assert delivery.volunteer_id != target_vol.pk
