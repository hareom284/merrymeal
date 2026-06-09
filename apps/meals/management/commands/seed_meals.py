from django.core.management.base import BaseCommand

from apps.meals.models import Meal

SEED_MEALS: list[dict] = [
    {
        "name": "Pumpkin & lentil curry",
        "description": "Mild coconut-curry with roast pumpkin and red lentils.",
        "prep_time_minutes": 15,
        "cook_time_minutes": 30,
    },
    {
        "name": "Chicken & vegetable rice bowl",
        "description": "Poached chicken thigh, steamed rice, seasonal greens.",
        "prep_time_minutes": 10,
        "cook_time_minutes": 25,
    },
    {
        "name": "Beef shepherd's pie",
        "description": "Beef mince ragu topped with mashed potato.",
        "prep_time_minutes": 20,
        "cook_time_minutes": 40,
    },
    {
        "name": "Tofu stir-fry with noodles",
        "description": "Soy-glazed tofu, broccoli and capsicum over noodles.",
        "prep_time_minutes": 10,
        "cook_time_minutes": 15,
    },
    {
        "name": "Lamb & sweet potato stew",
        "description": "Slow-cooked lamb shoulder with sweet potato and carrot.",
        "prep_time_minutes": 15,
        "cook_time_minutes": 90,
    },
]


class Command(BaseCommand):
    help = "Idempotently seed a small library of demo meals."

    def handle(self, *args, **options):
        created = 0
        for row in SEED_MEALS:
            _, was_created = Meal.objects.update_or_create(
                name=row["name"],
                defaults={
                    "description": row["description"],
                    "prep_time_minutes": row["prep_time_minutes"],
                    "cook_time_minutes": row["cook_time_minutes"],
                    "is_active": True,
                },
            )
            if was_created:
                created += 1
        self.stdout.write(
            self.style.SUCCESS(
                f"seed_meals: {created} new, "
                f"{len(SEED_MEALS) - created} updated. "
                f"Total now: {Meal.objects.count()}."
            )
        )
