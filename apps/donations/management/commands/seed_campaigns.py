from django.core.management.base import BaseCommand

from apps.donations.models import Campaign
from apps.donations.services.donate import GENERAL_FUND_SLUG


class Command(BaseCommand):
    help = (
        "Seed the catch-all 'General Fund' Campaign row. The public donate "
        "page (apps.donations.services.donate._resolve_campaign) falls back "
        "to this row for any donation that isn't pinned to a specific "
        "campaign. A fresh DB without this row 500s on /donate/start/. "
        "Idempotent on slug='general-fund'."
    )

    def handle(self, *args, **options):
        campaign, created = Campaign.objects.get_or_create(
            slug=GENERAL_FUND_SLUG,
            defaults={
                "name": "General Fund",
                "goal_cents": 0,
                "is_active": True,
            },
        )
        verb = "created" if created else "already present"
        self.stdout.write(
            self.style.SUCCESS(f"seed_campaigns: {verb} → {campaign.name} ({campaign.slug})")
        )
