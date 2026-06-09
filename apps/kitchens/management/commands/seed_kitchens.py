from decimal import Decimal

from django.core.management.base import BaseCommand

from apps.kitchens.models import Kitchen

SEED_KITCHENS: list[dict] = [
    {
        "name": "MerryMeal Central Kitchen",
        "latitude": Decimal("-37.8136"),
        "longitude": Decimal("144.9631"),
        "service_radius_km": Decimal("10.00"),
        "is_outsourced": False,
    },
    {
        "name": "MerryMeal North (Coburg)",
        "latitude": Decimal("-37.7411"),
        "longitude": Decimal("144.9650"),
        "service_radius_km": Decimal("8.00"),
        "is_outsourced": False,
    },
    {
        "name": "MerryMeal East (Box Hill)",
        "latitude": Decimal("-37.8200"),
        "longitude": Decimal("145.1224"),
        "service_radius_km": Decimal("8.00"),
        "is_outsourced": False,
    },
]


class Command(BaseCommand):
    help = "Idempotently seed default kitchens (Melbourne CBD + 2 suburb sites)."

    def handle(self, *args, **options):
        created = 0
        for row in SEED_KITCHENS:
            _, was_created = Kitchen.objects.update_or_create(
                name=row["name"],
                defaults={
                    "latitude": row["latitude"],
                    "longitude": row["longitude"],
                    "service_radius_km": row["service_radius_km"],
                    "is_outsourced": row["is_outsourced"],
                },
            )
            if was_created:
                created += 1
        self.stdout.write(
            self.style.SUCCESS(
                f"seed_kitchens: {created} new, "
                f"{len(SEED_KITCHENS) - created} updated. "
                f"Total now: {Kitchen.objects.count()}."
            )
        )
