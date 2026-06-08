import factory

from apps.partners.models import Partner


class PartnerFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Partner

    legal_name = factory.Sequence(lambda n: f"Partner Org {n}")
    type = "charity"
