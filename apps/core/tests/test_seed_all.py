import pytest
from django.core.management import call_command

from apps.accounts.models import Address, City, User
from apps.dietary.models import Allergy, DietPreference
from apps.donations.models import Campaign
from apps.kitchens.models import Ingredient, Kitchen
from apps.meals.models import Meal
from apps.planning.models import MealPlan
from apps.volunteers.models import Availability


def _expected_member_count():
    return User.objects.filter(role="member", is_active=True).count()


def _expected_volunteer_count():
    return User.objects.filter(role="volunteer", is_active=True).count()


@pytest.mark.django_db
def test_seed_all_runs_every_seeder(monkeypatch):
    monkeypatch.setenv("DJANGO_ADMIN_PASSWORD", "test-admin-pass-1234")
    call_command("seed_all")
    assert User.objects.filter(role="admin", is_superuser=True).count() == 1
    assert City.objects.count() == 5
    assert DietPreference.objects.count() == 8
    assert Allergy.objects.count() == 7
    assert Ingredient.objects.count() == 30
    assert Kitchen.objects.count() == 3
    assert Meal.objects.count() == 5
    assert Address.objects.count() == _expected_member_count()
    assert Availability.objects.count() == _expected_volunteer_count() * 21
    assert MealPlan.objects.count() == Kitchen.objects.count()
    assert Campaign.objects.filter(slug="general-fund").count() == 1


@pytest.mark.django_db
def test_seed_all_is_idempotent(monkeypatch):
    monkeypatch.setenv("DJANGO_ADMIN_PASSWORD", "test-admin-pass-1234")
    call_command("seed_all")
    call_command("seed_all")
    assert User.objects.filter(role="admin", is_superuser=True).count() == 1
    assert City.objects.count() == 5
    assert DietPreference.objects.count() == 8
    assert Allergy.objects.count() == 7
    assert Ingredient.objects.count() == 30
    assert Kitchen.objects.count() == 3
    assert Meal.objects.count() == 5
    assert Address.objects.count() == _expected_member_count()
    assert Availability.objects.count() == _expected_volunteer_count() * 21
    assert MealPlan.objects.count() == Kitchen.objects.count()
    assert Campaign.objects.filter(slug="general-fund").count() == 1
