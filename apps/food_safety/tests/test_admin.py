import pytest
from django.contrib.admin.sites import site

from apps.food_safety.models import FoodSafetyCheck

pytestmark = pytest.mark.django_db


def test_food_safety_check_registered_in_admin():
    assert site.is_registered(FoodSafetyCheck)


def test_admin_list_display():
    model_admin = site._registry[FoodSafetyCheck]
    assert "kitchen" in model_admin.list_display
    assert "check_type" in model_admin.list_display
    assert "result" in model_admin.list_display
    assert "checked_at" in model_admin.list_display
    assert "checked_by" in model_admin.list_display


def test_admin_list_filter():
    model_admin = site._registry[FoodSafetyCheck]
    assert "kitchen" in model_admin.list_filter
    assert "result" in model_admin.list_filter
    assert "check_type" in model_admin.list_filter
