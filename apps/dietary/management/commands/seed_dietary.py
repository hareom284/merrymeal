from django.core.management.base import BaseCommand

from apps.dietary.models import Allergy, DietPreference
from apps.kitchens.models import Ingredient

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

# Allergy name -> list of substring patterns to match ingredients by
# (case-insensitive). Minimum set for v1; the dietitian extends via admin.
#
# Allergy names here are the canonical lowercase set from ALLERGIES above —
# the story spec uses Capitalised aliases (Peanut, Milk, Wheat, Fish) but we
# reuse the project's canonical names so the allergies table stays at seven
# rows (the existing schema tests pin the set). "Milk" maps to "dairy" and
# "Wheat" maps to "gluten". Fish is intentionally not seeded — fish and
# shellfish allergies are medically distinct, so the dietitian should add a
# separate "fish" allergy row + mappings via admin rather than merging here.
#
# Substring match is best-effort: "egg" matches "eggplant" (false positive),
# which is why `--audit` exists. We accept the false-positive risk for v1 —
# the dietitian curates corrections via the admin.
SEED_INGREDIENT_ALLERGENS = {
    "peanut": ["peanut", "peanut oil"],
    "shellfish": ["prawn", "shrimp", "crab", "lobster"],
    "dairy": ["cow milk", "butter", "cheese"],
    "egg": ["egg"],
    "gluten": ["wheat flour", "bread", "pasta"],
    "soy": ["soy sauce", "tofu", "edamame"],
    "tree nut": ["almond", "cashew", "walnut"],
}


class Command(BaseCommand):
    help = (
        "Seed the diet_preferences and allergies tables and tag ingredients "
        "with the allergens they contain. Idempotent."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--audit",
            action="store_true",
            help="List ingredients with zero allergen tags and exit.",
        )

    def handle(self, *args, **options):
        if options["audit"]:
            self._audit()
            return

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

        added, present = self._link_ingredient_allergens()

        self.stdout.write(
            self.style.SUCCESS(
                f"seed_dietary: diet_preferences {dp_created}/{len(DIET_PREFERENCES)} new; "
                f"allergies {al_created}/{len(ALLERGIES)} new; "
                f"linked {added} new ingredient-allergen pair(s), {present} already present."
            )
        )

    def _link_ingredient_allergens(self) -> tuple[int, int]:
        added = present = 0
        for allergy_name, terms in SEED_INGREDIENT_ALLERGENS.items():
            allergy, _ = Allergy.objects.get_or_create(name=allergy_name)
            for term in terms:
                for ing in Ingredient.objects.filter(name__icontains=term):
                    if ing.contains_allergens.filter(pk=allergy.pk).exists():
                        present += 1
                    else:
                        ing.contains_allergens.add(allergy)
                        added += 1
        return added, present

    def _audit(self) -> None:
        untagged = Ingredient.objects.filter(
            contains_allergens__isnull=True,
        ).order_by("name")
        count = untagged.count()
        self.stdout.write(f"{count} ingredient(s) with no allergen tag:")
        for ing in untagged:
            self.stdout.write(f"  - {ing.name}")
