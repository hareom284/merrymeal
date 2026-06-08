import pytest
from django.contrib.admin.sites import site
from django.core.management import call_command

from apps.kitchens.models import Ingredient
from apps.kitchens.tests.factories import IngredientFactory


pytestmark = pytest.mark.django_db


class TestIngredientModel:
    def test_str_is_name(self):
        i = IngredientFactory(name="Pumpkin")
        assert str(i) == "Pumpkin"

    def test_db_table(self):
        assert Ingredient._meta.db_table == "ingredients"

    def test_unit_choices_match_schema(self):
        unit_field = Ingredient._meta.get_field("unit")
        codes = {code for code, _ in unit_field.choices}
        assert codes == {"g", "kg", "ml", "l", "unit"}


class TestIngredientAdmin:
    def test_ingredient_is_registered(self):
        assert site.is_registered(Ingredient)

    def test_search_and_filter_configured(self):
        admin = site._registry[Ingredient]
        assert "name" in admin.search_fields
        assert "unit" in admin.list_filter


class TestSeedIngredientsCommand:
    def test_creates_thirty_rows(self):
        call_command("seed_ingredients", verbosity=0)
        assert Ingredient.objects.count() == 30

    def test_is_idempotent(self):
        call_command("seed_ingredients", verbosity=0)
        call_command("seed_ingredients", verbosity=0)
        assert Ingredient.objects.count() == 30

    def test_seeds_have_valid_units(self):
        call_command("seed_ingredients", verbosity=0)
        valid = {"g", "kg", "ml", "l", "unit"}
        assert set(Ingredient.objects.values_list("unit", flat=True)).issubset(valid)

    def test_includes_core_staples(self):
        call_command("seed_ingredients", verbosity=0)
        names = set(Ingredient.objects.values_list("name", flat=True))
        for staple in ("Rice", "Pumpkin", "Chicken breast", "Coconut milk"):
            assert staple in names, f"missing staple: {staple}"
