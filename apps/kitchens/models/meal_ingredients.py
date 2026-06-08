from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models


class MealIngredient(models.Model):
    meal = models.ForeignKey(
        "meals.Meal",
        on_delete=models.PROTECT,
        related_name="meal_ingredients",
        db_column="meal_id",
    )
    ingredient = models.ForeignKey(
        "kitchens.Ingredient",
        on_delete=models.PROTECT,
        related_name="used_in_meals",
        db_column="ingredient_id",
    )
    quantity = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )

    class Meta:
        app_label = "kitchens"
        db_table = "meal_ingredients"
        constraints = [
            models.UniqueConstraint(
                fields=["meal", "ingredient"],
                name="uq_meal_ingredient",
            )
        ]

    def __str__(self) -> str:
        return f"{self.meal.name} — {self.ingredient.name} ({self.quantity})"
