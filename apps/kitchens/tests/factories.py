from datetime import date, timedelta
from decimal import Decimal

import factory

from apps.kitchens.models import Ingredient, IngredientBatch, Kitchen


class KitchenFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Kitchen

    name = factory.Sequence(lambda n: f"Kitchen {n}")
    is_outsourced = False
    latitude = Decimal("-37.8136")
    longitude = Decimal("144.9631")
    service_radius_km = Decimal("10.00")


class IngredientFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Ingredient

    name = factory.Sequence(lambda n: f"Ingredient {n}")
    unit = "g"


class MealIngredientFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "kitchens.MealIngredient"

    meal = factory.SubFactory("apps.meals.tests.factories.MealFactory")
    ingredient = factory.SubFactory(IngredientFactory)
    quantity = Decimal("100.00")


class IngredientBatchFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = IngredientBatch

    ingredient = factory.SubFactory(IngredientFactory)
    kitchen = factory.SubFactory(KitchenFactory)
    lot_number = factory.Sequence(lambda n: f"LOT-{n:05d}")
    quantity = Decimal("10.00")
    received_at = factory.LazyFunction(date.today)
    expiration_date = factory.LazyFunction(lambda: date.today() + timedelta(days=7))
