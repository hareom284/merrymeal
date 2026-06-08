from django.conf import settings
from django.db import models


class FoodSafetyCheck(models.Model):
    class CheckType(models.TextChoices):
        STORAGE_TEMP = "storage_temp", "Storage temperature"
        COOKING_TEMP = "cooking_temp", "Cooking temperature"
        COLD_CHAIN = "cold_chain", "Cold chain"
        HYGIENE = "hygiene", "Hygiene"
        CLEANING = "cleaning", "Cleaning"
        PEST_CONTROL = "pest_control", "Pest control"

    class Result(models.TextChoices):
        PASS = "pass", "Pass"
        FAIL = "fail", "Fail"

    kitchen = models.ForeignKey(
        "kitchens.Kitchen",
        on_delete=models.PROTECT,
        db_column="kitchen_id",
        related_name="safety_checks",
    )
    meal_plan = models.ForeignKey(
        "meals.MealPlan",
        on_delete=models.PROTECT,
        db_column="meal_plan_id",
        related_name="safety_checks",
        null=True,
        blank=True,
    )
    check_type = models.CharField(max_length=20, choices=CheckType.choices)
    temperature_celsius = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )
    result = models.CharField(max_length=4, choices=Result.choices)
    checked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        db_column="checked_by",
        related_name="safety_checks",
    )
    checked_at = models.DateTimeField()
    notes = models.TextField(null=True, blank=True)

    class Meta:
        db_table = "food_safety_checks"
        indexes = [
            models.Index(fields=["kitchen"], name="idx_fsc_kitchen"),
            models.Index(fields=["meal_plan"], name="idx_fsc_plan"),
        ]

    def __str__(self) -> str:
        return f"{self.check_type} @ {self.kitchen_id} = {self.result}"
