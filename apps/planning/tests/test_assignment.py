import datetime as dt
import math

import pytest

from apps.accounts.tests.factories import UserAddressFactory, UserFactory
from apps.core.geo import EARTH_RADIUS_KM
from apps.kitchens.tests.factories import KitchenFactory
from apps.planning.services.assignment import assign_meal_type
from apps.planning.services.exceptions import AddressMissingError

KITCHEN_LAT, KITCHEN_LNG = -37.8136, 144.9631
INSIDE_LAT, INSIDE_LNG = -37.8200, 144.9700
OUTSIDE_LAT, OUTSIDE_LNG = -37.6000, 144.9631

MONDAY = dt.date(2026, 6, 1)
SATURDAY = dt.date(2026, 6, 6)
SUNDAY = dt.date(2026, 6, 7)


@pytest.fixture
def kitchen(db):
    return KitchenFactory(
        latitude=KITCHEN_LAT,
        longitude=KITCHEN_LNG,
        service_radius_km=10,
    )


def _member_with(lat, lng):
    member = UserFactory(role="member")
    UserAddressFactory(user=member, latitude=lat, longitude=lng)
    return member


@pytest.mark.django_db
class TestAssignMealType:
    def test_weekday_inside_radius_is_fresh(self, kitchen):
        member = _member_with(INSIDE_LAT, INSIDE_LNG)
        assert assign_meal_type(member, kitchen, MONDAY) == "fresh"

    def test_weekday_outside_radius_is_frozen(self, kitchen):
        member = _member_with(OUTSIDE_LAT, OUTSIDE_LNG)
        assert assign_meal_type(member, kitchen, MONDAY) == "frozen"

    @pytest.mark.parametrize("day", [SATURDAY, SUNDAY])
    def test_weekend_is_always_frozen(self, kitchen, day):
        member = _member_with(INSIDE_LAT, INSIDE_LNG)
        assert assign_meal_type(member, kitchen, day) == "frozen"

    def test_exactly_at_radius_is_fresh(self, kitchen):
        # Exact 10 km meridian step using the same Earth radius constant
        # haversine_km uses, so distance == radius (within float precision)
        # and the `<=` boundary case is genuinely exercised.
        boundary_lat = KITCHEN_LAT + math.degrees(10 / EARTH_RADIUS_KM)
        member = _member_with(boundary_lat, KITCHEN_LNG)
        assert assign_meal_type(member, kitchen, MONDAY) == "fresh"

    def test_no_primary_address_raises(self, kitchen):
        member = UserFactory(role="member")
        with pytest.raises(AddressMissingError):
            assign_meal_type(member, kitchen, MONDAY)
