from django.core.management.base import BaseCommand
from django.db import transaction

from apps.accounts.models import User
from apps.volunteers.models import Availability

DAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
PHRASES = ["morning", "afternoon", "evening"]


class Command(BaseCommand):
    help = (
        "Give every active volunteer a full grid of availability "
        "(7 days x 3 phrases = 21 slots) so route packing always has "
        "an eligible driver. Idempotent."
    )

    def handle(self, *args, **options):
        volunteers = User.objects.filter(role="volunteer", is_active=True).order_by("id")
        created = 0
        with transaction.atomic():
            for vol in volunteers:
                for day in DAYS:
                    for phrase in PHRASES:
                        _, was_created = Availability.objects.get_or_create(
                            volunteer=vol,
                            day_of_week=day,
                            day_phrase=phrase,
                        )
                        if was_created:
                            created += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"seed_availability: {created} new slots. "
                f"Total now: {Availability.objects.count()} across "
                f"{volunteers.count()} volunteer(s)."
            )
        )
