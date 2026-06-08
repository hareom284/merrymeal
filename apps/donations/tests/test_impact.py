"""Unit tests for ``apps.donations.services.impact.meals_for_amount``.

Pure helper — no DB needed. ``override_settings`` exercises the
``MEAL_COST_CENTS`` knob so ops can tune the conversion without a
deploy.
"""
import pytest
from django.test import override_settings

from apps.donations.services.impact import meals_for_amount


def test_thirty_dollars_equals_ten_meals():
    # $30 / $3 per meal = 10 meals.
    assert meals_for_amount(30_00) == 10


def test_one_dollar_floors_to_zero():
    # $1 buys zero meals at $3/meal — floor, not round.
    assert meals_for_amount(1_00) == 0


def test_three_dollar_boundary_is_exactly_one_meal():
    # Exact boundary — $3 buys exactly one meal.
    assert meals_for_amount(3_00) == 1


def test_just_under_three_dollars_is_zero_meals():
    # 299c < 300c — floor division keeps it at zero.
    assert meals_for_amount(2_99) == 0


def test_zero_is_zero_meals():
    assert meals_for_amount(0) == 0


def test_negative_amount_raises():
    # Negative cents is a programming error upstream, not a refund.
    with pytest.raises(ValueError):
        meals_for_amount(-1)


def test_float_input_raises_type_error():
    # Money is integer cents. A float here means a caller is doing the
    # wrong thing — fail loudly at the boundary.
    with pytest.raises(TypeError):
        meals_for_amount(30.0)


def test_bool_input_raises_type_error():
    # ``True`` is also ``int`` in Python — explicit check rejects it so
    # ``meals_for_amount(True)`` doesn't silently return 0.
    with pytest.raises(TypeError):
        meals_for_amount(True)


@override_settings(MEAL_COST_CENTS=500)
def test_setting_override_changes_conversion():
    # $30 / $5 per meal = 6 meals — proves the setting is read lazily
    # inside the function (cached at import would break this test).
    assert meals_for_amount(30_00) == 6
