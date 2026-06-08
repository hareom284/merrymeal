import pytest

from apps.dietary.tests.factories import AllergyFactory
from apps.kitchens.tests.factories import IngredientFactory


@pytest.mark.django_db
def test_ingredient_can_have_allergens():
    ing = IngredientFactory(name="peanut")
    a = AllergyFactory(name="Peanut")
    ing.contains_allergens.add(a)
    assert list(ing.contains_allergens.all()) == [a]
