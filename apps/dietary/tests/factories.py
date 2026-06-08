import factory

from apps.dietary.models import Allergy, DietPreference


class AllergyFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Allergy
        django_get_or_create = ("name",)

    name = factory.Sequence(lambda n: f"Allergy {n}")


class DietPreferenceFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = DietPreference
        django_get_or_create = ("name",)

    name = factory.Sequence(lambda n: f"Diet {n}")
