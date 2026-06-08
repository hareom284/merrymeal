from django.db import models


class MealPlan(models.Model):
    """Stub model — full implementation in Epic 03. Exists so FoodSafetyCheck.meal_plan FK resolves."""

    class Meta:
        app_label = "meals"
        db_table = "meal_plans"
