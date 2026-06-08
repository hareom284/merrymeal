from decimal import Decimal

import pytest

from apps.accounts.tests.factories import UserFactory
from apps.food_safety.models import FoodSafetyCheck
from apps.food_safety.tests.factories import FoodSafetyCheckFactory
from apps.kitchens.tests.factories import KitchenFactory


pytestmark = pytest.mark.django_db


def test_table_is_named_food_safety_checks():
    assert FoodSafetyCheck._meta.db_table == "food_safety_checks"


def test_required_fields_persist():
    kitchen = KitchenFactory()
    user = UserFactory()
    check = FoodSafetyCheckFactory(
        kitchen=kitchen,
        checked_by=user,
        check_type=FoodSafetyCheck.CheckType.COOKING_TEMP,
        temperature_celsius=Decimal("75.50"),
        result=FoodSafetyCheck.Result.PASS,
    )
    check.refresh_from_db()
    assert check.kitchen_id == kitchen.id
    assert check.checked_by_id == user.id
    assert check.temperature_celsius == Decimal("75.50")
    assert check.result == "pass"
    assert check.meal_plan_id is None


def test_hygiene_check_allows_null_temperature():
    check = FoodSafetyCheckFactory(
        kitchen=KitchenFactory(),
        checked_by=UserFactory(),
        check_type=FoodSafetyCheck.CheckType.HYGIENE,
        temperature_celsius=None,
        result=FoodSafetyCheck.Result.PASS,
        notes="Bench wiped down at 10:00.",
    )
    check.refresh_from_db()
    assert check.temperature_celsius is None
    assert check.notes == "Bench wiped down at 10:00."


def test_column_names_match_sql_schema():
    columns = {f.column for f in FoodSafetyCheck._meta.get_fields() if hasattr(f, "column")}
    assert {"kitchen_id", "meal_plan_id", "check_type",
            "temperature_celsius", "result", "checked_by",
            "checked_at", "notes"} <= columns


def test_indexes_cover_kitchen_and_meal_plan():
    indexed_columns = set()
    for idx in FoodSafetyCheck._meta.indexes:
        indexed_columns.update(idx.fields)
    assert {"kitchen", "meal_plan"} <= indexed_columns
