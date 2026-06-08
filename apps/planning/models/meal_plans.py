from django.conf import settings
from django.db import models


class MealPlan(models.Model):
    """One planned meal per (kitchen, service_date).

    Schema-only. The fresh/frozen automation lives in
    apps.planning.services.assignment (Story 3.2); the planner UI sets
    meal_type at write time (Story 3.3).
    """

    DAY_CHOICES = [
        ("mon", "Mon"), ("tue", "Tue"), ("wed", "Wed"),
        ("thu", "Thu"), ("fri", "Fri"),
        ("sat", "Sat"), ("sun", "Sun"),
    ]

    TYPE_CHOICES = [
        ("fresh", "Fresh"),
        ("frozen", "Frozen"),
    ]

    meal = models.ForeignKey(
        "meals.Meal", on_delete=models.PROTECT, related_name="plans"
    )
    kitchen = models.ForeignKey(
        "kitchens.Kitchen", on_delete=models.PROTECT, related_name="plans"
    )
    service_date = models.DateField()
    day_of_week = models.CharField(max_length=3, choices=DAY_CHOICES)
    meal_type = models.CharField(
        max_length=6, choices=TYPE_CHOICES, default="fresh"
    )
    planned_quantity = models.PositiveIntegerField(default=0)
    published_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="published_meal_plans",
    )
    warnings_acknowledged_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="acknowledged_meal_plans",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "planning"
        db_table = "meal_plans"
        constraints = [
            models.UniqueConstraint(
                fields=["kitchen", "service_date"],
                name="uq_meal_plan_kitchen_date",
            ),
        ]
        indexes = [
            models.Index(fields=["service_date"], name="idx_plan_date"),
        ]

    def __str__(self) -> str:
        return f"{self.kitchen_id}/{self.service_date} -> meal {self.meal_id}"
