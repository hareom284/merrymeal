import factory
from django.utils import timezone
from factory.django import DjangoModelFactory

from apps.donations.models import Campaign, Donation


class CampaignFactory(DjangoModelFactory):
    class Meta:
        model = Campaign

    name = factory.Sequence(lambda n: f"Campaign {n}")
    slug = factory.Sequence(lambda n: f"campaign-{n}")
    goal_cents = 1_000_00
    is_active = True
    start_at = factory.LazyFunction(timezone.now)


class DonationFactory(DjangoModelFactory):
    class Meta:
        model = Donation

    campaign = factory.SubFactory(CampaignFactory)
    donor_email = factory.Sequence(lambda n: f"donor{n}@example.com")
    amount_cents = 5_000  # $50.00
    payment_type = "card"
    status = "pending"
