from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.accounts.models import Address, City, User

MELBOURNE_LAT = Decimal("-37.8136")
MELBOURNE_LNG = Decimal("144.9631")
LABEL = "Home"


class Command(BaseCommand):
    help = (
        "Give every member a primary 'Home' address with Melbourne lat/lng "
        "so the dispatcher's closest-kitchen lookup has something to chew "
        "on. Idempotent on (user, label='Home'). Requires seed_cities and "
        "seed_test_users to have run first."
    )

    def handle(self, *args, **options):
        city = City.objects.order_by("id").first()
        if city is None:
            self.stderr.write(
                self.style.ERROR(
                    "seed_addresses: no City rows — run seed_cities first."
                )
            )
            return

        members = User.objects.filter(role="member", is_active=True).order_by("id")
        created = 0
        with transaction.atomic():
            for member in members:
                _, was_created = Address.objects.update_or_create(
                    user=member,
                    label=LABEL,
                    defaults={
                        "city": city,
                        "postal_code": "3000",
                        "latitude": MELBOURNE_LAT,
                        "longitude": MELBOURNE_LNG,
                    },
                )
                if was_created:
                    created += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"seed_addresses: {created} new, "
                f"{members.count() - created} updated. "
                f"Total addresses now: {Address.objects.count()}."
            )
        )
