import pytest
from django.core.management import call_command

from apps.accounts.models import City, User
from apps.dietary.models import Allergy, DietPreference
from apps.kitchens.models import Ingredient


@pytest.mark.django_db
def test_seed_all_runs_every_seeder(monkeypatch):
    monkeypatch.setenv("DJANGO_ADMIN_PASSWORD", "test-admin-pass-1234")
    call_command("seed_all")
    assert User.objects.filter(role="admin", is_superuser=True).count() == 1
    assert City.objects.count() == 5
    assert DietPreference.objects.count() == 8
    assert Allergy.objects.count() == 7
    assert Ingredient.objects.count() == 30


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
