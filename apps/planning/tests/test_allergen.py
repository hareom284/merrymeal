import pytest

from apps.accounts.tests.factories import UserFactory
from apps.dietary.tests.factories import AllergyFactory
from apps.kitchens.tests.factories import IngredientFactory, MealIngredientFactory
from apps.meals.tests.factories import MealFactory


def _link(meal, ingredient):
    """Attach an ingredient to a meal via the MealIngredient through-table
    (which has a required ``quantity`` field)."""
    MealIngredientFactory(meal=meal, ingredient=ingredient)


@pytest.mark.django_db
class TestMealAllergensForMember:
    def test_no_overlap_returns_empty(self):
        from apps.planning.services.allergen import meal_allergens_for_member

        meal = MealFactory()
        _link(meal, IngredientFactory(name="rice"))
        member = UserFactory(role="member")
        assert meal_allergens_for_member(meal, member) == []

    def test_member_has_no_allergies(self):
        from apps.planning.services.allergen import meal_allergens_for_member

        peanut = AllergyFactory(name="Peanut")
        ing = IngredientFactory(name="peanut")
        ing.contains_allergens.add(peanut)
        meal = MealFactory()
        _link(meal, ing)
        member = UserFactory(role="member")
        assert meal_allergens_for_member(meal, member) == []

    def test_one_match(self):
        from apps.planning.services.allergen import meal_allergens_for_member

        peanut = AllergyFactory(name="Peanut")
        ing = IngredientFactory(name="peanut")
        ing.contains_allergens.add(peanut)
        member = UserFactory(role="member")
        member.allergies.add(peanut)
        meal = MealFactory()
        _link(meal, ing)
        result = meal_allergens_for_member(meal, member)
        assert [a.name for a in result] == ["Peanut"]

    def test_multiple_ingredients_share_one_allergen_deduped(self):
        from apps.planning.services.allergen import meal_allergens_for_member

        milk = AllergyFactory(name="Milk")
        butter = IngredientFactory(name="butter")
        cheese = IngredientFactory(name="cheese")
        butter.contains_allergens.add(milk)
        cheese.contains_allergens.add(milk)
        member = UserFactory(role="member")
        member.allergies.add(milk)
        meal = MealFactory()
        _link(meal, butter)
        _link(meal, cheese)
        result = meal_allergens_for_member(meal, member)
        assert len(result) == 1
        assert result[0].name == "Milk"
