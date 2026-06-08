import factory
from django.contrib.auth import get_user_model

from apps.accounts.models import Address, CaregiverLink, City

User = get_user_model()


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User
        django_get_or_create = ("email",)
        skip_postgeneration_save = True

    email = factory.Sequence(lambda n: f"user{n}@example.com")
    full_name = factory.Faker("name")
    role = "member"
    is_active = True

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        password = kwargs.pop("password", "pw12345!")
        return model_class.objects.create_user(password=password, **kwargs)


class CityFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = City
        django_get_or_create = ("name",)

    name = factory.Sequence(lambda n: f"City {n}")


class AddressFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Address

    user = factory.SubFactory(UserFactory)
    city = factory.SubFactory(CityFactory)
    label = "Home"
    postal_code = factory.Sequence(lambda n: f"3{n:03d}")


# Alias used by sprint-06 stories that follow the UserAddressFactory naming convention.
UserAddressFactory = AddressFactory


class MemberCaregiverLinkFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = CaregiverLink

    member = factory.SubFactory(UserFactory, role="member")
    caregiver = factory.SubFactory(UserFactory, role="caregiver")
    relationship = "family"
