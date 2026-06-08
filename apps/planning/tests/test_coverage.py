"""Story 3.6 — diet-coverage warning service tests."""
import datetime as dt

import pytest

from apps.accounts.tests.factories import UserAddressFactory, UserFactory
from apps.dietary.tests.factories import DietPreferenceFactory
from apps.kitchens.tests.factories import KitchenFactory
from apps.meals.tests.factories import MealFactory
from apps.planning.tests.factories import MealPlanFactory

KITCHEN_LAT, KITCHEN_LNG = -37.81, 144.96
INSIDE_LAT, INSIDE_LNG = -37.82, 144.97
WEDNESDAY = dt.date(2026, 6, 3)
SATURDAY = dt.date(2026, 6, 6)


@pytest.mark.django_db
class TestDietWarnings:
    def test_meal_tagged_for_all_diets_returns_empty(self):
        from apps.planning.services.coverage import diet_warnings

        halal = DietPreferenceFactory(name="Halal")
        kitchen = KitchenFactory(
            latitude=KITCHEN_LAT, longitude=KITCHEN_LNG, service_radius_km=10
        )
        member = UserFactory(role="member")
        UserAddressFactory(user=member, latitude=INSIDE_LAT, longitude=INSIDE_LNG)
        member.diet_preferences.add(halal)
        meal = MealFactory()
        meal.diets.add(halal)
        plan = MealPlanFactory(
            meal=meal, kitchen=kitchen, service_date=WEDNESDAY
        )
        assert diet_warnings(plan) == {}

    def test_meal_missing_diet_tag_returns_counts(self):
        from apps.planning.services.coverage import diet_warnings

        halal = DietPreferenceFactory(name="Halal")
        kitchen = KitchenFactory(
            latitude=KITCHEN_LAT, longitude=KITCHEN_LNG, service_radius_km=10
        )
        for _ in range(3):
            m = UserFactory(role="member")
            UserAddressFactory(user=m, latitude=INSIDE_LAT, longitude=INSIDE_LNG)
            m.diet_preferences.add(halal)
        plan = MealPlanFactory(
            meal=MealFactory(),  # NOT tagged halal
            kitchen=kitchen,
            service_date=WEDNESDAY,
        )
        result = diet_warnings(plan)
        assert result == {halal: 3}

    def test_weekend_is_excluded_from_warning(self):
        from apps.planning.services.coverage import diet_warnings

        halal = DietPreferenceFactory(name="Halal")
        kitchen = KitchenFactory(
            latitude=KITCHEN_LAT, longitude=KITCHEN_LNG, service_radius_km=10
        )
        m = UserFactory(role="member")
        UserAddressFactory(user=m, latitude=INSIDE_LAT, longitude=INSIDE_LNG)
        m.diet_preferences.add(halal)
        plan = MealPlanFactory(
            meal=MealFactory(), kitchen=kitchen, service_date=SATURDAY
        )
        assert diet_warnings(plan) == {}


@pytest.mark.django_db
def test_acknowledge_sets_user():
    from apps.planning.services.coverage import acknowledge

    plan = MealPlanFactory()
    admin = UserFactory(role="admin")
    acknowledge(plan, admin)
    plan.refresh_from_db()
    assert plan.warnings_acknowledged_by_id == admin.id


@pytest.mark.django_db
def test_upsert_cell_clears_acknowledgement():
    from apps.planning.services.planner import upsert_cell

    plan = MealPlanFactory()
    plan.warnings_acknowledged_by = plan.published_by
    plan.save()
    assert plan.warnings_acknowledged_by_id is not None

    new_meal = MealFactory()
    updated = upsert_cell(
        kitchen=plan.kitchen,
        meal=new_meal,
        service_date=plan.service_date,
        planned_quantity=plan.planned_quantity,
        published_by=plan.published_by,
    )
    assert updated.warnings_acknowledged_by_id is None
