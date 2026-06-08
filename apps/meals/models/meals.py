from django.db import models

from apps.core.models.soft_delete import SoftDeleteModel


class Meal(SoftDeleteModel):
    name = models.CharField(max_length=160)
    description = models.TextField(null=True, blank=True)
    prep_time_minutes = models.PositiveIntegerField(null=True, blank=True)
    cook_time_minutes = models.PositiveIntegerField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    ingredients = models.ManyToManyField(
        "kitchens.Ingredient",
        through="kitchens.MealIngredient",
        through_fields=("meal", "ingredient"),
        related_name="meals",
        blank=True,
    )
    diets = models.ManyToManyField(
        "dietary.DietPreference",
        related_name="compatible_meals",
        blank=True,
    )

    class Meta:
        app_label = "meals"
        db_table = "meals"

    def __str__(self) -> str:
        return self.name
