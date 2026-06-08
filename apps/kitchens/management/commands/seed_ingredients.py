from django.core.management.base import BaseCommand

from apps.kitchens.models import Ingredient

SEED_INGREDIENTS: list[tuple[str, str]] = [
    # Staples
    ("Rice", "kg"),
    ("Pasta", "kg"),
    ("Bread", "unit"),
    ("Potato", "kg"),
    ("Sweet potato", "kg"),
    # Proteins
    ("Chicken breast", "kg"),
    ("Chicken thigh", "kg"),
    ("Beef mince", "kg"),
    ("Lamb shoulder", "kg"),
    ("Fish fillet", "kg"),
    ("Tofu", "kg"),
    ("Lentils", "kg"),
    ("Chickpeas", "kg"),
    ("Egg", "unit"),
    # Vegetables
    ("Pumpkin", "kg"),
    ("Carrot", "kg"),
    ("Onion", "kg"),
    ("Garlic", "kg"),
    ("Tomato", "kg"),
    ("Spinach", "kg"),
    ("Broccoli", "kg"),
    ("Capsicum", "kg"),
    ("Zucchini", "kg"),
    # Pantry
    ("Olive oil", "l"),
    ("Coconut milk", "ml"),
    ("Soy sauce", "ml"),
    ("Salt", "g"),
    ("Pepper", "g"),
    ("Curry powder", "g"),
    ("Stock cube", "unit"),
]


class Command(BaseCommand):
    help = "Idempotently seed 30 common ingredients used by demo recipes."

    def handle(self, *args, **options):
        created = 0
        for name, unit in SEED_INGREDIENTS:
            _, was_created = Ingredient.objects.update_or_create(
                name=name, defaults={"unit": unit}
            )
            if was_created:
                created += 1
        self.stdout.write(
            self.style.SUCCESS(
                f"seed_ingredients: {created} new, "
                f"{len(SEED_INGREDIENTS) - created} updated. "
                f"Total now: {Ingredient.objects.count()}."
            )
        )
