import factory
from django.utils import timezone

from apps.accounts.tests.factories import UserFactory
from apps.kitchens.tests.factories import KitchenFactory
from apps.meals.tests.factories import MealFactory
from apps.planning.models import MealPlan


class MealPlanFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = MealPlan

    meal = factory.SubFactory(MealFactory)
    kitchen = factory.SubFactory(KitchenFactory)
    service_date = factory.LazyFunction(timezone.localdate)
    day_of_week = factory.LazyAttribute(
        lambda o: ["mon", "tue", "wed", "thu", "fri", "sat", "sun"][o.service_date.weekday()]
    )
    meal_type = "fresh"
    planned_quantity = 20
    published_by = factory.SubFactory(UserFactory, role="admin")
