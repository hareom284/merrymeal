import pytest

from apps.food_safety.forms.check import CheckForm
from apps.food_safety.models import FoodSafetyCheck


pytestmark = pytest.mark.django_db


def _payload(**overrides):
    base = {
        "check_type": FoodSafetyCheck.CheckType.STORAGE_TEMP,
        "temperature_celsius": "4.0",
        "result": "",
        "notes": "",
    }
    base.update(overrides)
    return base


def test_temp_type_requires_temperature():
    form = CheckForm(_payload(temperature_celsius=""))
    assert not form.is_valid()
    assert "temperature_celsius" in form.errors


def test_hygiene_type_requires_result_radio():
    form = CheckForm(_payload(
        check_type=FoodSafetyCheck.CheckType.HYGIENE,
        temperature_celsius="",
        result="",
    ))
    assert not form.is_valid()
    assert "result" in form.errors


def test_hygiene_type_ignores_stray_temperature():
    form = CheckForm(_payload(
        check_type=FoodSafetyCheck.CheckType.HYGIENE,
        temperature_celsius="4.0",
        result=FoodSafetyCheck.Result.PASS,
    ))
    assert form.is_valid(), form.errors
    assert form.cleaned_data["temperature_celsius"] is None


def test_temp_type_clears_result_radio_input():
    form = CheckForm(_payload(result=FoodSafetyCheck.Result.FAIL))
    assert form.is_valid(), form.errors
    assert form.cleaned_data["result"] == ""
