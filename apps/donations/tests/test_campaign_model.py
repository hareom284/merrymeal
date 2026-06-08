import pytest
from django.utils import timezone

from apps.donations.models import Campaign


@pytest.mark.django_db
def test_campaign_stores_goal_in_integer_cents():
    c = Campaign.objects.create(
        name="Winter appeal 2026",
        slug="winter-appeal-2026",
        goal_cents=5_000_00,  # $5,000.00
        start_at=timezone.now(),
        is_active=True,
    )
    assert c.goal_cents == 500_000
    assert isinstance(c.goal_cents, int)  # never a Decimal, never a float


@pytest.mark.django_db
def test_campaign_str_uses_name():
    c = Campaign.objects.create(name="General fund", slug="general", goal_cents=0)
    assert str(c) == "General fund"
