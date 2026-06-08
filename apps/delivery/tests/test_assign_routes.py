"""Unit tests for the route packer (Story 4.7).

Date pinning uses the in-house `freezer` fixture from
`apps/delivery/tests/conftest.py` (freezegun isn't a project dep).
"""
import datetime as dt
import logging
from decimal import Decimal

import pytest

from apps.accounts.tests.factories import UserAddressFactory, UserFactory
from apps.delivery.models import Delivery, Route
from apps.delivery.services.dispatch import (
    PackReport,
    assign_routes_for_date,
)
from apps.delivery.tests.factories import DeliveryFactory
from apps.kitchens.tests.factories import KitchenFactory
from apps.planning.tests.factories import MealPlanFactory
from apps.volunteers.tests.factories import (
    AvailabilityFactory,
    VolunteerFactory,
)

MELB_CBD = (Decimal("-37.8136"), Decimal("144.9631"))


@pytest.fixture
def kitchen_in_cbd(db):
    return KitchenFactory(latitude=MELB_CBD[0], longitude=MELB_CBD[1])


def _seed_deliveries(kitchen, plan, count: int, placeholder):
    """Helper: create N deliveries near the kitchen, all unrouted."""
    out = []
    for i in range(count):
        member = UserFactory(role="member")
        address = UserAddressFactory(
            user=member,
            latitude=Decimal("-37.82") - Decimal(f"0.00{i:02d}"),
            longitude=Decimal("144.97") + Decimal(f"0.00{i:02d}"),
        )
        out.append(DeliveryFactory(
            member=member,
            member_address=address,
            meal_plan=plan,
            volunteer=placeholder,
            scheduled_date=plan.service_date,
            status="pending",
            route=None,
        ))
    return out


@pytest.mark.django_db
def test_six_deliveries_two_volunteers_makes_two_routes_of_three(
    freezer, kitchen_in_cbd,
):
    freezer.move_to("2026-06-15")  # Monday
    plan = MealPlanFactory(
        kitchen=kitchen_in_cbd, service_date=dt.date(2026, 6, 15),
    )
    placeholder = VolunteerFactory(email="placeholder@vol.test")
    _seed_deliveries(kitchen_in_cbd, plan, 6, placeholder)

    for i in range(2):
        vol = VolunteerFactory(email=f"vol{i}@example.com")
        AvailabilityFactory(volunteer=vol, day_of_week="mon", day_phrase="morning")

    report = assign_routes_for_date(dt.date(2026, 6, 15))

    assert isinstance(report, PackReport)
    assert len(report.routes_created) == 2
    for route in report.routes_created:
        assert route.deliveries.count() == 3


@pytest.mark.django_db
def test_capacity_capped_at_twelve_overflow_unassigned(
    freezer, kitchen_in_cbd, caplog,
):
    freezer.move_to("2026-06-15")
    plan = MealPlanFactory(
        kitchen=kitchen_in_cbd, service_date=dt.date(2026, 6, 15),
    )
    placeholder = VolunteerFactory(email="placeholder@vol.test")
    _seed_deliveries(kitchen_in_cbd, plan, 30, placeholder)

    only_vol = VolunteerFactory(email="solo@example.com")
    AvailabilityFactory(volunteer=only_vol, day_of_week="mon", day_phrase="morning")

    with caplog.at_level(logging.WARNING, logger="merrymeal.dispatch"):
        report = assign_routes_for_date(dt.date(2026, 6, 15))

    assert len(report.routes_created) == 1
    assert report.routes_created[0].deliveries.count() == 12
    assert len(report.unassigned) == 18
    assert any(
        "overflow" in r.message and "unassigned=18" in r.message
        for r in caplog.records
    )


@pytest.mark.django_db
def test_no_volunteers_no_exception(freezer, kitchen_in_cbd, caplog):
    freezer.move_to("2026-06-15")
    plan = MealPlanFactory(
        kitchen=kitchen_in_cbd, service_date=dt.date(2026, 6, 15),
    )
    placeholder = VolunteerFactory(email="placeholder@vol.test")
    deliveries = _seed_deliveries(kitchen_in_cbd, plan, 4, placeholder)

    with caplog.at_level(logging.WARNING, logger="merrymeal.dispatch"):
        report = assign_routes_for_date(dt.date(2026, 6, 15))

    assert report.routes_created == []
    assert len(report.unassigned) == 4
    for d in deliveries:
        d.refresh_from_db()
        assert d.route is None


@pytest.mark.django_db
def test_idempotent_rerun_same_groups(freezer, kitchen_in_cbd):
    freezer.move_to("2026-06-15")
    plan = MealPlanFactory(
        kitchen=kitchen_in_cbd, service_date=dt.date(2026, 6, 15),
    )
    placeholder = VolunteerFactory(email="placeholder@vol.test")
    _seed_deliveries(kitchen_in_cbd, plan, 6, placeholder)
    for i in range(2):
        vol = VolunteerFactory(email=f"vol{i}@example.com")
        AvailabilityFactory(volunteer=vol, day_of_week="mon", day_phrase="morning")

    first = assign_routes_for_date(dt.date(2026, 6, 15))
    second = assign_routes_for_date(dt.date(2026, 6, 15))

    # Clean-slate strategy: route ids differ, counts and membership match.
    assert len(first.routes_created) == 2
    assert len(second.routes_created) == 2
    assert sorted(r.deliveries.count() for r in second.routes_created) == [3, 3]
    # No delivery should end up routed twice or orphaned.
    assert Delivery.objects.filter(
        scheduled_date=dt.date(2026, 6, 15), route__isnull=True,
    ).count() == 0


@pytest.mark.django_db
def test_afternoon_volunteer_not_picked_for_morning_route(
    freezer, kitchen_in_cbd,
):
    freezer.move_to("2026-06-15")
    plan = MealPlanFactory(
        kitchen=kitchen_in_cbd, service_date=dt.date(2026, 6, 15),
    )
    placeholder = VolunteerFactory(email="placeholder@vol.test")
    _seed_deliveries(kitchen_in_cbd, plan, 3, placeholder)

    afternoon_only = VolunteerFactory(email="afternoon@example.com")
    AvailabilityFactory(
        volunteer=afternoon_only, day_of_week="mon", day_phrase="afternoon",
    )

    report = assign_routes_for_date(dt.date(2026, 6, 15))

    assert report.routes_created == []
    assert len(report.unassigned) == 3


@pytest.mark.django_db
def test_inprogress_routes_from_prior_runs_are_left_alone(
    freezer, kitchen_in_cbd,
):
    """Idempotency: only `planned` routes get wiped between runs."""
    freezer.move_to("2026-06-15")
    plan = MealPlanFactory(
        kitchen=kitchen_in_cbd, service_date=dt.date(2026, 6, 15),
    )
    placeholder = VolunteerFactory(email="placeholder@vol.test")
    vol = VolunteerFactory(email="vol@example.com")
    AvailabilityFactory(volunteer=vol, day_of_week="mon", day_phrase="morning")

    # A leftover in-progress route from an earlier run.
    leftover = Route.objects.create(
        volunteer=vol,
        route_date=dt.date(2026, 6, 15),
        status=Route.STATUS_IN_PROGRESS,
    )
    _seed_deliveries(kitchen_in_cbd, plan, 3, placeholder)

    assign_routes_for_date(dt.date(2026, 6, 15))

    leftover.refresh_from_db()
    assert leftover.status == Route.STATUS_IN_PROGRESS  # untouched
