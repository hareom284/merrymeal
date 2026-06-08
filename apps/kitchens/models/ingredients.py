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

    class Meta:
        app_label = "kitchens"
        db_table = "ingredients"

    def __str__(self) -> str:
        return self.name
