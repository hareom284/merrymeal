from django.core.management.base import BaseCommand

from apps.accounts.models import City


STARTER_CITIES = ["Melbourne", "Geelong", "Ballarat", "Bendigo", "Frankston"]


class Command(BaseCommand):
    help = "Seed the cities table with starter Victorian cities. Idempotent."

    def handle(self, *args, **options):
        created = 0
        for name in STARTER_CITIES:
            _, was_created = City.objects.get_or_create(name=name)
            if was_created:
                created += 1
        self.stdout.write(
            self.style.SUCCESS(
                f"seed_cities: {created} created, {len(STARTER_CITIES) - created} already existed."
            )
        )
