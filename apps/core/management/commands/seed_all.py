from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Run every project seed command in order. Idempotent — safe to re-run."

    SEED_COMMANDS = [
        "seed_admin",
        "seed_cities",
        "seed_dietary",
        "seed_ingredients",
        "seed_kitchens",
        "seed_meals",
        "seed_test_users",
        "seed_addresses",
        "seed_availability",
        "seed_meal_plans",
        "seed_campaigns",
    ]

    def handle(self, *args, **options):
        for name in self.SEED_COMMANDS:
            self.stdout.write(self.style.NOTICE(f"→ {name}"))
            call_command(name, stdout=self.stdout, stderr=self.stderr)
        self.stdout.write(
            self.style.SUCCESS(f"seed_all: ran {len(self.SEED_COMMANDS)} seeders.")
        )
