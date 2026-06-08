import datetime as dt

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from apps.planning.models import MealPlan
from apps.planning.tests.factories import MealPlanFactory


@pytest.mark.django_db
class TestMealPlanModel:
    def test_can_create_a_plan(self):
        plan = MealPlanFactory()
        assert plan.pk is not None
        assert plan.meal_type == "fresh"
        assert plan.planned_quantity == 20

    def test_db_table_name_is_meal_plans(self):
        assert MealPlan._meta.db_table == "meal_plans"

    def test_unique_kitchen_service_date(self):
        plan = MealPlanFactory(service_date=dt.date(2026, 6, 15))
        with pytest.raises(IntegrityError):
            MealPlanFactory(
                kitchen=plan.kitchen,
                service_date=dt.date(2026, 6, 15),
            )

    def test_different_kitchens_same_date_ok(self):
        first = MealPlanFactory(service_date=dt.date(2026, 6, 15))
        second = MealPlanFactory(service_date=dt.date(2026, 6, 15))
        assert first.kitchen_id != second.kitchen_id

    def test_meal_type_choices_enforced(self):
        plan = MealPlanFactory.build(meal_type="lukewarm")
        with pytest.raises(ValidationError):
            plan.full_clean()
