import factory

from apps.accounts.tests.factories import UserFactory
from apps.volunteers.models import Availability


class VolunteerFactory(UserFactory):
    role = "volunteer"


class AvailabilityFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Availability

    volunteer = factory.SubFactory(VolunteerFactory)
    day_of_week = "mon"
    day_phrase = "morning"
