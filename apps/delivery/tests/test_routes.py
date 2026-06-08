import datetime as dt

import pytest

from apps.delivery.models import Route
from apps.delivery.tests.factories import RouteFactory
from apps.volunteers.tests.factories import VolunteerFactory


@pytest.mark.django_db
def test_route_persists_with_defaults():
    route = RouteFactory()
    assert route.pk is not None
    assert route.status == "planned"
    assert route.created_at is not None
    assert route.updated_at is not None


@pytest.mark.django_db
def test_route_db_table_matches_schema():
    assert Route._meta.db_table == "routes"


@pytest.mark.django_db
def test_status_choices_match_schema():
    assert {c for c, _ in Route.STATUS_CHOICES} == {
        "planned",
        "in_progress",
        "completed",
        "cancelled",
    }


@pytest.mark.django_db
def test_route_can_transition_statuses():
    route = RouteFactory()
    for new_status in ("in_progress", "completed"):
        route.status = new_status
        route.save()
        route.refresh_from_db()
        assert route.status == new_status


@pytest.mark.django_db
def test_two_routes_same_volunteer_same_day_allowed():
    vol = VolunteerFactory()
    today = dt.date.today()
    RouteFactory(volunteer=vol, route_date=today)
    RouteFactory(volunteer=vol, route_date=today)
    assert Route.objects.filter(volunteer=vol, route_date=today).count() == 2


@pytest.mark.django_db
def test_str_includes_date_and_volunteer():
    route = RouteFactory(route_date=dt.date(2026, 6, 15))
    s = str(route)
    assert "2026-06-15" in s
