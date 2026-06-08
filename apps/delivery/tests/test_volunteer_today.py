"""Tests for Story 4.8 — Volunteer "today" route screen.

Covers:
* `apps.delivery.services.volunteer_today.get_today_route` — shape, scoping,
  current-stop detection, empty-route handling.
* `GET /volunteer/today/` — auth via `@role_required`, 403 for members,
  200 for the route's own volunteer, rendered member-display string.

Adaptations from the spec:
* `User` has no `first_name` / `last_name` — the model is `full_name`
  (see apps/accounts/models/users.py). The service derives "Margaret S."
  from `full_name.split()`. Tests use `full_name="Margaret Smith"`.
* `pytest-freezer` is not installed; we monkeypatch the service module's
  `timezone.localdate` (same pattern as
  `apps/dashboards/tests/test_member_today_service.py`).
* `RouteFactory` and `DeliveryFactory` already live in
  `apps/delivery/tests/factories.py` from Sprint 07, so we import them
  directly (not re-create them).
"""
from __future__ import annotations

import datetime as dt

import pytest
from django.urls import reverse

from apps.accounts.tests.factories import UserFactory
from apps.delivery.tests.factories import DeliveryFactory, RouteFactory

FROZEN_TODAY = dt.date(2026, 6, 9)


@pytest.fixture
def frozen_today(monkeypatch):
    """Pin ``timezone.localdate()`` inside the volunteer_today service."""
    from apps.delivery.services import volunteer_today as svc

    monkeypatch.setattr(svc.timezone, "localdate", lambda: FROZEN_TODAY)
    return FROZEN_TODAY


@pytest.mark.django_db
def test_get_today_route_returns_only_user_deliveries(frozen_today):
    from apps.delivery.services.volunteer_today import get_today_route

    sarah = UserFactory(role="volunteer")
    other = UserFactory(role="volunteer")
    sarah_route = RouteFactory(volunteer=sarah, route_date=frozen_today)
    DeliveryFactory.create_batch(
        3,
        route=sarah_route,
        volunteer=sarah,
        scheduled_date=frozen_today,
    )
    other_route = RouteFactory(volunteer=other, route_date=frozen_today)
    DeliveryFactory.create_batch(
        2,
        route=other_route,
        volunteer=other,
        scheduled_date=frozen_today,
    )

    data = get_today_route(sarah)
    assert len(data["stops"]) == 3
    assert all(s["delivery"].volunteer_id == sarah.id for s in data["stops"])


@pytest.mark.django_db
def test_current_stop_is_first_pending(frozen_today):
    from apps.delivery.services.volunteer_today import get_today_route

    sarah = UserFactory(role="volunteer")
    route = RouteFactory(volunteer=sarah, route_date=frozen_today)
    DeliveryFactory(
        route=route, volunteer=sarah, status="delivered",
        scheduled_date=frozen_today,
    )
    d2 = DeliveryFactory(
        route=route, volunteer=sarah, status="pending",
        scheduled_date=frozen_today,
    )
    DeliveryFactory(
        route=route, volunteer=sarah, status="pending",
        scheduled_date=frozen_today,
    )

    stops = get_today_route(sarah)["stops"]
    current = [s for s in stops if s["is_current"]]
    assert len(current) == 1
    assert current[0]["delivery"].id == d2.id


@pytest.mark.django_db
def test_empty_route_returns_empty_stops_no_error(frozen_today):
    from apps.delivery.services.volunteer_today import get_today_route

    sarah = UserFactory(role="volunteer")
    data = get_today_route(sarah)
    assert data["stops"] == []
    assert data["route"] is None


@pytest.mark.django_db
def test_stops_are_ordered_by_delivery_id(frozen_today):
    """The greedy-nearest order is encoded by insertion id (Story 4.7).

    The service must read deliveries in `id` order — never re-sort.
    """
    from apps.delivery.services.volunteer_today import get_today_route

    sarah = UserFactory(role="volunteer")
    route = RouteFactory(volunteer=sarah, route_date=frozen_today)
    d_a = DeliveryFactory(route=route, volunteer=sarah, scheduled_date=frozen_today)
    d_b = DeliveryFactory(route=route, volunteer=sarah, scheduled_date=frozen_today)
    d_c = DeliveryFactory(route=route, volunteer=sarah, scheduled_date=frozen_today)

    stops = get_today_route(sarah)["stops"]
    ids = [s["delivery"].id for s in stops]
    assert ids == [d_a.id, d_b.id, d_c.id]


@pytest.mark.django_db
def test_member_display_uses_last_initial(frozen_today):
    from apps.delivery.services.volunteer_today import get_today_route

    sarah = UserFactory(role="volunteer")
    member = UserFactory(role="member", full_name="Margaret Smith")
    route = RouteFactory(volunteer=sarah, route_date=frozen_today)
    DeliveryFactory(
        route=route, volunteer=sarah, member=member,
        scheduled_date=frozen_today,
    )

    stops = get_today_route(sarah)["stops"]
    assert stops[0]["member_display"] == "Margaret S."


@pytest.mark.django_db
def test_view_blocks_non_volunteer(client, frozen_today):
    member = UserFactory(role="member")
    client.force_login(member)
    resp = client.get(reverse("delivery:volunteer_today"))
    assert resp.status_code == 403


@pytest.mark.django_db
def test_view_blocks_admin(client, frozen_today):
    admin = UserFactory(role="admin")
    client.force_login(admin)
    resp = client.get(reverse("delivery:volunteer_today"))
    assert resp.status_code == 403


@pytest.mark.django_db
def test_view_renders_member_display_with_initial(client, frozen_today):
    sarah = UserFactory(role="volunteer")
    member = UserFactory(role="member", full_name="Margaret Smith")
    route = RouteFactory(volunteer=sarah, route_date=frozen_today)
    DeliveryFactory(
        route=route, volunteer=sarah, member=member,
        scheduled_date=frozen_today,
    )
    client.force_login(sarah)
    resp = client.get(reverse("delivery:volunteer_today"))
    assert resp.status_code == 200
    assert b"Margaret S." in resp.content


@pytest.mark.django_db
def test_view_empty_state_for_volunteer_with_no_deliveries(client, frozen_today):
    sarah = UserFactory(role="volunteer")
    client.force_login(sarah)
    resp = client.get(reverse("delivery:volunteer_today"))
    assert resp.status_code == 200
    assert b"All done" in resp.content
