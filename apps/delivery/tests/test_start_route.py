"""Tests for the volunteer "I'm on my way" / start-route transition.

Service contract
----------------
``apps.delivery.services.start_route.start_route(volunteer)`` flips the
volunteer's ``Route`` for today from ``planned`` to ``in_progress`` and
bulk-updates that route's ``pending`` deliveries to ``out_for_delivery``.
``delivered`` and ``failed`` deliveries are untouched. The function is
idempotent: calling it twice does not double-fire status changes.

View contract
-------------
``POST /volunteer/route/start/`` (name ``delivery:start_route``):

* @role_required("volunteer") — members + admins get 403.
* GET → 405 (POST-only).
* Success → re-renders ``delivery/volunteer/_route_fragment.html`` so an
  HTMX swap target of ``#route-fragment`` updates in place. The route's
  stops now carry ``out_for_delivery`` status, which the member-side
  tracking page uses to reveal the live map block.

Time pinning follows the same in-house ``freezer`` pattern used by
``test_volunteer_today.py``: monkeypatch the service module's
``timezone.localdate``.
"""
from __future__ import annotations

import datetime as dt

import pytest
from django.urls import reverse

from apps.accounts.tests.factories import UserFactory
from apps.delivery.models import Delivery, Route
from apps.delivery.tests.factories import DeliveryFactory, RouteFactory

FROZEN_TODAY = dt.date(2026, 6, 9)


@pytest.fixture
def frozen_today(monkeypatch):
    """Pin ``timezone.localdate()`` inside the start_route service."""
    from apps.delivery.services import start_route as svc

    monkeypatch.setattr(svc.timezone, "localdate", lambda: FROZEN_TODAY)
    return FROZEN_TODAY


# ---------------------------------------------------------------- service ---


@pytest.mark.django_db
def test_start_route_flips_route_to_in_progress(frozen_today):
    from apps.delivery.services.start_route import start_route

    sarah = UserFactory(role="volunteer")
    route = RouteFactory(volunteer=sarah, route_date=frozen_today, status="planned")
    DeliveryFactory(
        route=route, volunteer=sarah, status="pending",
        scheduled_date=frozen_today,
    )

    returned = start_route(sarah)

    assert returned is not None
    assert returned.pk == route.pk
    route.refresh_from_db()
    assert route.status == Route.STATUS_IN_PROGRESS


@pytest.mark.django_db
def test_start_route_bulk_updates_pending_to_out_for_delivery(frozen_today):
    from apps.delivery.services.start_route import start_route

    sarah = UserFactory(role="volunteer")
    route = RouteFactory(volunteer=sarah, route_date=frozen_today)
    DeliveryFactory.create_batch(
        3,
        route=route,
        volunteer=sarah,
        status="pending",
        scheduled_date=frozen_today,
    )

    start_route(sarah)

    assert Delivery.objects.filter(
        route=route, status="out_for_delivery"
    ).count() == 3
    assert not Delivery.objects.filter(
        route=route, status="pending"
    ).exists()


@pytest.mark.django_db
def test_start_route_leaves_delivered_and_failed_alone(frozen_today):
    """Re-entrance safety: a mid-route call must not rewind closed stops."""
    from apps.delivery.services.start_route import start_route

    sarah = UserFactory(role="volunteer")
    route = RouteFactory(volunteer=sarah, route_date=frozen_today)
    delivered = DeliveryFactory(
        route=route, volunteer=sarah, status="delivered",
        scheduled_date=frozen_today,
    )
    failed = DeliveryFactory(
        route=route, volunteer=sarah, status="failed",
        scheduled_date=frozen_today,
    )
    pending = DeliveryFactory(
        route=route, volunteer=sarah, status="pending",
        scheduled_date=frozen_today,
    )

    start_route(sarah)

    delivered.refresh_from_db()
    failed.refresh_from_db()
    pending.refresh_from_db()
    assert delivered.status == "delivered"
    assert failed.status == "failed"
    assert pending.status == "out_for_delivery"


@pytest.mark.django_db
def test_start_route_is_idempotent(frozen_today):
    """A second call (e.g. accidental double-tap) must not raise or
    re-touch already-flipped rows. The route stays ``in_progress`` and
    deliveries stay ``out_for_delivery``."""
    from apps.delivery.services.start_route import start_route

    sarah = UserFactory(role="volunteer")
    route = RouteFactory(volunteer=sarah, route_date=frozen_today)
    DeliveryFactory(
        route=route, volunteer=sarah, status="pending",
        scheduled_date=frozen_today,
    )

    start_route(sarah)
    start_route(sarah)  # double-tap

    route.refresh_from_db()
    assert route.status == Route.STATUS_IN_PROGRESS
    assert Delivery.objects.filter(
        route=route, status="out_for_delivery"
    ).count() == 1


@pytest.mark.django_db
def test_start_route_returns_none_when_no_route_today(frozen_today):
    from apps.delivery.services.start_route import start_route

    sarah = UserFactory(role="volunteer")
    # Route exists but on a different date — must be ignored.
    RouteFactory(
        volunteer=sarah,
        route_date=frozen_today - dt.timedelta(days=1),
        status="planned",
    )

    assert start_route(sarah) is None


@pytest.mark.django_db
def test_start_route_scopes_to_volunteer(frozen_today):
    """Volunteer A starting their route must not flip volunteer B's
    deliveries — a regression here would prematurely notify other
    routes' members."""
    from apps.delivery.services.start_route import start_route

    sarah = UserFactory(role="volunteer")
    other = UserFactory(role="volunteer")
    sarah_route = RouteFactory(volunteer=sarah, route_date=frozen_today)
    other_route = RouteFactory(volunteer=other, route_date=frozen_today)
    DeliveryFactory(
        route=sarah_route, volunteer=sarah, status="pending",
        scheduled_date=frozen_today,
    )
    other_delivery = DeliveryFactory(
        route=other_route, volunteer=other, status="pending",
        scheduled_date=frozen_today,
    )

    start_route(sarah)

    other_route.refresh_from_db()
    other_delivery.refresh_from_db()
    assert other_route.status == "planned"
    assert other_delivery.status == "pending"


# ------------------------------------------------------------------- view ---


@pytest.mark.django_db
def test_view_blocks_member(client, frozen_today):
    member = UserFactory(role="member")
    client.force_login(member)
    resp = client.post(reverse("delivery:start_route"))
    assert resp.status_code == 403


@pytest.mark.django_db
def test_view_blocks_admin(client, frozen_today):
    admin = UserFactory(role="admin")
    client.force_login(admin)
    resp = client.post(reverse("delivery:start_route"))
    assert resp.status_code == 403


@pytest.mark.django_db
def test_view_rejects_get(client, frozen_today):
    sarah = UserFactory(role="volunteer")
    client.force_login(sarah)
    resp = client.get(reverse("delivery:start_route"))
    assert resp.status_code == 405


@pytest.mark.django_db
def test_view_renders_route_fragment(client, frozen_today, monkeypatch):
    """Happy path — POST flips the route and returns the swap target so
    HTMX can ``outerHTML``-replace ``#route-fragment``."""
    # The volunteer_today service uses its OWN timezone.localdate
    # reference; pin both so the post-flip re-render sees today's stops.
    from apps.delivery.services import volunteer_today as today_svc

    monkeypatch.setattr(today_svc.timezone, "localdate", lambda: FROZEN_TODAY)

    sarah = UserFactory(role="volunteer")
    route = RouteFactory(volunteer=sarah, route_date=frozen_today)
    DeliveryFactory(
        route=route, volunteer=sarah, status="pending",
        scheduled_date=frozen_today,
    )

    client.force_login(sarah)
    resp = client.post(reverse("delivery:start_route"))
    assert resp.status_code == 200
    assert b'id="route-fragment"' in resp.content
    route.refresh_from_db()
    assert route.status == Route.STATUS_IN_PROGRESS


@pytest.mark.django_db
def test_view_no_route_today_is_a_noop_render(client, frozen_today, monkeypatch):
    """Volunteer hits Start before any route exists for them — the
    fragment renders the empty state, no error."""
    from apps.delivery.services import volunteer_today as today_svc

    monkeypatch.setattr(today_svc.timezone, "localdate", lambda: FROZEN_TODAY)

    sarah = UserFactory(role="volunteer")
    client.force_login(sarah)
    resp = client.post(reverse("delivery:start_route"))
    assert resp.status_code == 200
    assert b"All done" in resp.content
