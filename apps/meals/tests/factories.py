import factory

from apps.meals.models import Meal


class MealFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Meal

    name = factory.Sequence(lambda n: f"Meal {n}")
    description = "Test description"
    prep_time_minutes = 15
    cook_time_minutes = 30
    is_active = True
