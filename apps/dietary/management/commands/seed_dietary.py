from django.core.management.base import BaseCommand

from apps.dietary.models import Allergy, DietPreference


DIET_PREFERENCES = [
    "vegetarian",
    "vegan",
    "halal",
    "kosher",
    "gluten-free",
    "diabetic-friendly",
    "low-sodium",
    "pureed",
]

ALLERGIES = [
    "peanut",
    "tree nut",
    "dairy",
    "egg",
    "soy",
    "shellfish",
    "gluten",
]


class Command(BaseCommand):
    help = "Seed the diet_preferences and allergies tables. Idempotent."

    def handle(self, *args, **options):
        dp_created = 0
        for name in DIET_PREFERENCES:
            _, was_created = DietPreference.objects.get_or_create(name=name)
            if was_created:
                dp_created += 1

        al_created = 0
        for name in ALLERGIES:
            _, was_created = Allergy.objects.get_or_create(name=name)
            if was_created:
                al_created += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"seed_dietary: diet_preferences {dp_created}/{len(DIET_PREFERENCES)} new; "
                f"allergies {al_created}/{len(ALLERGIES)} new."
            )
        )
