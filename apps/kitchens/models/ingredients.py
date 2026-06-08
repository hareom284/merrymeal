from django.db import models


class Ingredient(models.Model):
    UNIT_CHOICES = [
        ("g", "Gram"),
        ("kg", "Kilogram"),
        ("ml", "Millilitre"),
        ("l", "Litre"),
        ("unit", "Unit"),
    ]

    name = models.CharField(max_length=160)
    unit = models.CharField(max_length=10, choices=UNIT_CHOICES)
    contains_allergens = models.ManyToManyField(
        "dietary.Allergy",
        related_name="ingredients",
        through="kitchens.IngredientAllergy",
        blank=True,
    )

    class Meta:
        app_label = "kitchens"
        db_table = "ingredients"

    def __str__(self) -> str:
        return self.name


class IngredientAllergy(models.Model):
    """Join table: which allergens an ingredient contains.

    Substring-matched in seed_dietary; the dietitian can curate via admin.
    """

    ingredient = models.ForeignKey(
        "kitchens.Ingredient",
        on_delete=models.CASCADE,
        db_column="ingredient_id",
    )
    allergy = models.ForeignKey(
        "dietary.Allergy",
        on_delete=models.CASCADE,
        db_column="allergy_id",
    )

    class Meta:
        app_label = "kitchens"
        db_table = "ingredient_allergy"
        constraints = [
            models.UniqueConstraint(
                fields=["ingredient", "allergy"],
                name="uq_ingredient_allergy",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.ingredient_id} → {self.allergy_id}"
