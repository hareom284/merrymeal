from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.kitchens.models import Kitchen
from apps.meals.models import Meal
from apps.planning.models import MealPlan

_WEEKDAY_TO_ENUM = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]


class Command(BaseCommand):
    help = (
        "Publish one MealPlan per kitchen for today (Australia/Melbourne) "
        "so the dispatcher can bind a meal to each delivery. Idempotent on "
        "(kitchen, service_date). Requires seed_kitchens, seed_meals and "
        "seed_admin to have run first."
    )

    def handle(self, *args, **options):
        today = timezone.localdate()
        day_of_week = _WEEKDAY_TO_ENUM[today.weekday()]

        admin = (
            User.objects.filter(role="admin", is_superuser=True).order_by("id").first()
        )
        if admin is None:
            self.stderr.write(
                self.style.ERROR(
                    "seed_meal_plans: no admin user — run seed_admin first."
                )
            )
            return

        kitchens = list(Kitchen.objects.order_by("id"))
        meals = list(Meal.objects.filter(is_active=True).order_by("id"))
        if not kitchens or not meals:
            self.stderr.write(
                self.style.ERROR(
                    "seed_meal_plans: need at least one Kitchen and Meal — "
                    "run seed_kitchens and seed_meals first."
                )
            )
            return

        created = 0
        with transaction.atomic():
            for index, kitchen in enumerate(kitchens):
                meal = meals[index % len(meals)]
                _, was_created = MealPlan.objects.update_or_create(
                    kitchen=kitchen,
                    service_date=today,
                    defaults={
                        "meal": meal,
                        "day_of_week": day_of_week,
                        "meal_type": "fresh",
                        "planned_quantity": 20,
                        "published_by": admin,
                    },
                )
                if was_created:
                    created += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"seed_meal_plans: {created} new, "
                f"{len(kitchens) - created} updated for {today.isoformat()}."
            )
        )
