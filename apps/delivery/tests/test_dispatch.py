"""Unit tests for the daily dispatch service (Story 4.6).

Date pinning uses the in-house `freezer` fixture from
`apps/delivery/tests/conftest.py` (freezegun isn't a project dep).
"""
import datetime as dt
import logging
from decimal import Decimal

import pytest

from apps.accounts.tests.factories import UserAddressFactory, UserFactory
from apps.delivery.models import Delivery
from apps.delivery.services.dispatch import (
    DispatchReport,
    generate_deliveries_for_date,
)
from apps.kitchens.tests.factories import KitchenFactory
from apps.planning.tests.factories import MealPlanFactory
from apps.volunteers.tests.factories import VolunteerFactory

MELB_CBD = (Decimal("-37.8136"), Decimal("144.9631"))


@pytest.fixture
def placeholder_volunteer(db):
    return VolunteerFactory(email="placeholder@vol.test")


@pytest.fixture
def kitchen_in_cbd(db):
    return KitchenFactory(latitude=MELB_CBD[0], longitude=MELB_CBD[1])


def _make_member(lat=Decimal("-37.8200"), lon=Decimal("144.9700")):
    member = UserFactory(role="member")
    UserAddressFactory(user=member, latitude=lat, longitude=lon)
    return member


@pytest.mark.django_db
def test_three_members_one_plan_three_deliveries(
    freezer, placeholder_volunteer, kitchen_in_cbd,
):
    freezer.move_to("2026-06-15")  # Monday
    MealPlanFactory(kitchen=kitchen_in_cbd, service_date=dt.date(2026, 6, 15))
    for _ in range(3):
        _make_member()

    report = generate_deliveries_for_date(dt.date(2026, 6, 15))

    assert isinstance(report, DispatchReport)
    assert len(report.created) == 3
    assert Delivery.objects.filter(scheduled_date=dt.date(2026, 6, 15)).count() == 3


@pytest.mark.django_db
def test_idempotent_rerun_no_duplicates(
    freezer, placeholder_volunteer, kitchen_in_cbd,
):
    freezer.move_to("2026-06-15")
    MealPlanFactory(kitchen=kitchen_in_cbd, service_date=dt.date(2026, 6, 15))
    _make_member()
    _make_member()

    first = generate_deliveries_for_date(dt.date(2026, 6, 15))
    second = generate_deliveries_for_date(dt.date(2026, 6, 15))

    assert len(first.created) == 2
    assert len(second.created) == 0  # nothing new
    assert Delivery.objects.filter(scheduled_date=dt.date(2026, 6, 15)).count() == 2


@pytest.mark.django_db
def test_member_without_address_is_skipped_with_log(
    freezer, placeholder_volunteer, kitchen_in_cbd, caplog,
):
    freezer.move_to("2026-06-15")
    MealPlanFactory(kitchen=kitchen_in_cbd, service_date=dt.date(2026, 6, 15))
    homeless = UserFactory(role="member")  # no UserAddress

    with caplog.at_level(logging.WARNING, logger="merrymeal.dispatch"):
        report = generate_deliveries_for_date(dt.date(2026, 6, 15))

    assert len(report.created) == 0
    assert any(
        f"member={homeless.id}" in r.message and "no address" in r.message
        for r in caplog.records
    )


@pytest.mark.django_db
def test_no_plan_for_kitchen_skips_member(
    freezer, placeholder_volunteer, kitchen_in_cbd, caplog,
):
    freezer.move_to("2026-06-15")
    # Kitchen exists, but no MealPlan for the date.
    _make_member()

    with caplog.at_level(logging.WARNING, logger="merrymeal.dispatch"):
        report = generate_deliveries_for_date(dt.date(2026, 6, 15))

    assert len(report.created) == 0
    assert any("no meal plan" in r.message for r in caplog.records)


@pytest.mark.django_db
def test_weekend_run_yields_frozen_meal_type(
    freezer, placeholder_volunteer, kitchen_in_cbd,
):
    freezer.move_to("2026-06-13")  # Saturday
    MealPlanFactory(
        kitchen=kitchen_in_cbd,
        service_date=dt.date(2026, 6, 13),
        meal_type="frozen",
    )
    _make_member()

    report = generate_deliveries_for_date(dt.date(2026, 6, 13))

    assert len(report.created) == 1
    assert report.created[0].meal_type == "frozen"


@pytest.mark.django_db
def test_closest_kitchen_wins(freezer, placeholder_volunteer):
    freezer.move_to("2026-06-15")
    near = KitchenFactory(
        latitude=Decimal("-37.8200"), longitude=Decimal("144.9700"),
    )
    far = KitchenFactory(
        latitude=Decimal("-38.5000"), longitude=Decimal("145.5000"),
    )
    MealPlanFactory(kitchen=near, service_date=dt.date(2026, 6, 15))
    MealPlanFactory(kitchen=far, service_date=dt.date(2026, 6, 15))

    _make_member(lat=Decimal("-37.8210"), lon=Decimal("144.9710"))
    report = generate_deliveries_for_date(dt.date(2026, 6, 15))

    assert len(report.created) == 1
    assert report.created[0].meal_plan.kitchen_id == near.id
