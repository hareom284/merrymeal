from decimal import Decimal

import pytest
from django.utils import timezone

from apps.accounts.tests.factories import UserFactory
from apps.food_safety.models import FoodSafetyCheck
from apps.food_safety.services.checks import (
    derive_result,
    record_check,
    today_checks_for,
)
from apps.kitchens.tests.factories import KitchenFactory


pytestmark = pytest.mark.django_db


def test_record_check_writes_row_with_server_timestamp():
    kitchen = KitchenFactory()
    user = UserFactory()
    before = timezone.now()

    check = record_check(
        kitchen=kitchen,
        user=user,
        check_type=FoodSafetyCheck.CheckType.STORAGE_TEMP,
        temperature_celsius=Decimal("4.0"),
        result=None,
        notes="Walk-in fridge.",
    )

    assert check.id is not None
    assert check.checked_by_id == user.id
    assert check.kitchen_id == kitchen.id
    assert check.checked_at >= before
    assert check.result == "pass"


def test_record_check_fails_when_cooking_temp_too_low():
    check = record_check(
        kitchen=KitchenFactory(),
        user=UserFactory(),
        check_type=FoodSafetyCheck.CheckType.COOKING_TEMP,
        temperature_celsius=Decimal("60.0"),
        result=None,
        notes="",
    )
    assert check.result == "fail"


def test_record_check_for_hygiene_uses_explicit_result():
    check = record_check(
        kitchen=KitchenFactory(),
        user=UserFactory(),
        check_type=FoodSafetyCheck.CheckType.HYGIENE,
        temperature_celsius=None,
        result=FoodSafetyCheck.Result.FAIL,
        notes="Sink blocked.",
    )
    assert check.result == "fail"
    assert check.temperature_celsius is None


def test_derive_result_thresholds():
    assert derive_result("storage_temp", Decimal("4.0")) == "pass"
    assert derive_result("storage_temp", Decimal("8.0")) == "fail"
    assert derive_result("cooking_temp", Decimal("75.0")) == "pass"
    assert derive_result("cold_chain", Decimal("2.0")) == "pass"


def test_today_checks_for_returns_only_current_user_and_local_date(settings):
    kitchen = KitchenFactory()
    me = UserFactory()
    other = UserFactory()
    record_check(kitchen=kitchen, user=me,
                 check_type="hygiene", temperature_celsius=None,
                 result="pass", notes="")
    record_check(kitchen=kitchen, user=other,
                 check_type="hygiene", temperature_celsius=None,
                 result="pass", notes="")
    rows = today_checks_for(me)
    assert rows.count() == 1
    assert rows.first().checked_by_id == me.id
