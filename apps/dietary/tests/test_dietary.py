import pytest
from django.contrib import admin as django_admin
from django.core.management import call_command
from django.db import IntegrityError

from apps.accounts.models import User
from apps.accounts.tests.factories import UserFactory
from apps.dietary.models import (
    Allergy,
    DietPreference,
    UserAllergy,
    UserDietPreference,
)


# ---------- DietPreference / Allergy root models ----------


@pytest.mark.django_db
def test_diet_preference_can_be_created():
    p = DietPreference.objects.create(name="vegan")
    assert p.pk is not None
    assert p.name == "vegan"


@pytest.mark.django_db
def test_diet_preference_name_is_unique():
    DietPreference.objects.create(name="vegan")
    with pytest.raises(IntegrityError):
        DietPreference.objects.create(name="vegan")


@pytest.mark.django_db
def test_diet_preference_db_table():
    assert DietPreference._meta.db_table == "diet_preferences"


@pytest.mark.django_db
def test_allergy_db_table():
    assert Allergy._meta.db_table == "allergies"


@pytest.mark.django_db
def test_allergy_name_is_unique():
    Allergy.objects.create(name="peanut")
    with pytest.raises(IntegrityError):
        Allergy.objects.create(name="peanut")


# ---------- through models ----------


@pytest.mark.django_db
def test_user_diet_preference_through_table():
    assert UserDietPreference._meta.db_table == "diet_preference_user"


@pytest.mark.django_db
def test_user_allergy_through_table():
    assert UserAllergy._meta.db_table == "allergy_user"


@pytest.mark.django_db
def test_user_diet_preference_pair_is_unique():
    user = UserFactory()
    pref = DietPreference.objects.create(name="vegan")
    UserDietPreference.objects.create(user=user, diet_preference=pref)
    with pytest.raises(IntegrityError):
        UserDietPreference.objects.create(user=user, diet_preference=pref)


@pytest.mark.django_db
def test_user_allergy_pair_is_unique():
    user = UserFactory()
    a = Allergy.objects.create(name="peanut")
    UserAllergy.objects.create(user=user, allergy=a)
    with pytest.raises(IntegrityError):
        UserAllergy.objects.create(user=user, allergy=a)


@pytest.mark.django_db
def test_user_can_have_many_diet_preferences():
    user = UserFactory()
    vegan = DietPreference.objects.create(name="vegan")
    gf = DietPreference.objects.create(name="gluten-free")
    UserDietPreference.objects.create(user=user, diet_preference=vegan)
    UserDietPreference.objects.create(user=user, diet_preference=gf)
    assert UserDietPreference.objects.filter(user=user).count() == 2


# ---------- seed_dietary ----------


@pytest.mark.django_db
def test_seed_dietary_creates_8_diet_preferences():
    call_command("seed_dietary")
    names = set(DietPreference.objects.values_list("name", flat=True))
    assert names == {
        "vegetarian",
        "vegan",
        "halal",
        "kosher",
        "gluten-free",
        "diabetic-friendly",
        "low-sodium",
        "pureed",
    }


@pytest.mark.django_db
def test_seed_dietary_creates_7_allergies():
    call_command("seed_dietary")
    names = set(Allergy.objects.values_list("name", flat=True))
    assert names == {
        "peanut",
        "tree nut",
        "dairy",
        "egg",
        "soy",
        "shellfish",
        "gluten",
    }


@pytest.mark.django_db
def test_seed_dietary_is_idempotent():
    call_command("seed_dietary")
    call_command("seed_dietary")
    assert DietPreference.objects.count() == 8
    assert Allergy.objects.count() == 7


# ---------- admin ----------


def test_root_models_registered_in_admin():
    assert DietPreference in django_admin.site._registry
    assert Allergy in django_admin.site._registry


def test_user_admin_has_dietary_inlines():
    user_admin = django_admin.site._registry[User]
    inline_models = [inline.model for inline in user_admin.inlines]
    assert UserDietPreference in inline_models
    assert UserAllergy in inline_models
