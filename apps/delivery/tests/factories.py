import datetime as dt

import factory

from apps.delivery.models import Route
from apps.volunteers.tests.factories import VolunteerFactory


class RouteFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Route

    volunteer = factory.SubFactory(VolunteerFactory)
    route_date = factory.LazyFunction(dt.date.today)
    status = "planned"
