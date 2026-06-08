from decimal import Decimal

import pytest
from django.contrib.admin.sites import site
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from apps.kitchens.models import MealIngredient
from apps.kitchens.tests.factories import IngredientFactory, MealIngredientFactory
from apps.meals.models import Meal
from apps.meals.tests.factories import MealFactory

pytestmark = pytest.mark.django_db


class TestMealIngredientModel:
    def test_db_table(self):
        assert MealIngredient._meta.db_table == "meal_ingredients"

    def test_str(self):
        mi = MealIngredientFactory(
            meal=MealFactory(name="Pumpkin curry"),
            ingredient=IngredientFactory(name="Pumpkin"),
            quantity=Decimal("500.00"),
        )
        s = str(mi)
        assert "Pumpkin curry" in s and "Pumpkin" in s

    def test_unique_meal_ingredient_pair(self):
        meal = MealFactory()
        ing = IngredientFactory()
        MealIngredientFactory(meal=meal, ingredient=ing)
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                MealIngredientFactory(meal=meal, ingredient=ing)

    @pytest.mark.parametrize("bad_qty", [Decimal("0"), Decimal("-1.00")])
    def test_quantity_must_be_positive(self, bad_qty):
        mi = MealIngredientFactory.build(quantity=bad_qty)
        with pytest.raises(ValidationError):
            mi.full_clean()

    def test_quantity_accepts_two_decimal_places(self):
        mi = MealIngredientFactory(quantity=Decimal("12.34"))
        assert mi.quantity == Decimal("12.34")


class TestMealAdminInline:
    def test_meal_admin_has_meal_ingredient_inline(self):
        meal_admin = site._registry[Meal]
        model_classes = [inline.model for inline in meal_admin.inlines]
        assert MealIngredient in model_classes

    def test_inline_includes_quantity_field(self):
        meal_admin = site._registry[Meal]
        inline_cls = next(i for i in meal_admin.inlines if i.model is MealIngredient)
        assert inline_cls.fields is None or "quantity" in inline_cls.fields
