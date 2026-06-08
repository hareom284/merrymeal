import datetime as dt

import factory

from apps.delivery.models import Delivery, Route
from apps.volunteers.tests.factories import VolunteerFactory


class RouteFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Route

    volunteer = factory.SubFactory(VolunteerFactory)
    route_date = factory.LazyFunction(dt.date.today)
    status = "planned"


class DeliveryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Delivery

    member = factory.SubFactory(
        "apps.accounts.tests.factories.UserFactory", role="member"
    )
    member_address = factory.SubFactory(
        "apps.accounts.tests.factories.UserAddressFactory",
        user=factory.SelfAttribute("..member"),
    )
    meal_plan = factory.SubFactory("apps.planning.tests.factories.MealPlanFactory")
    volunteer = factory.SubFactory("apps.volunteers.tests.factories.VolunteerFactory")
    route = None
    meal_type = "fresh"
    status = "pending"
    scheduled_date = factory.LazyFunction(dt.date.today)
