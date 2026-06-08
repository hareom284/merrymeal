from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models


class IngredientBatch(models.Model):
    """A delivered batch of one ingredient sitting in one kitchen.

    Schema only. State-changing operations (receiving a batch, deducting on
    cook, writing off waste) live in apps.kitchens.services.stock.

    NOTE: quantity=0 is a valid terminal state after stock deduction (Sprint 06).
    The MinValueValidator only fires on receipt (full_clean() in receive_batch()).
    Stock-deduction writes quantity directly via save(update_fields=...).
    """

    ingredient = models.ForeignKey(
        "kitchens.Ingredient",
        on_delete=models.PROTECT,
        related_name="batches",
        db_column="ingredient_id",
    )
    kitchen = models.ForeignKey(
        "kitchens.Kitchen",
        on_delete=models.PROTECT,
        related_name="batches",
        db_column="kitchen_id",
    )
    lot_number = models.CharField(max_length=80, null=True, blank=True)
    quantity = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    received_at = models.DateField(null=True, blank=True)
    expiration_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "kitchens"
        db_table = "ingredient_batches"
        indexes = [
            models.Index(fields=["ingredient"], name="idx_batch_ingredient"),
            models.Index(fields=["kitchen"], name="idx_batch_kitchen"),
            models.Index(fields=["expiration_date"], name="idx_batch_expiry"),
        ]

    def __str__(self) -> str:
        lot = self.lot_number or "?"
        return f"{self.ingredient.name} [{lot}] exp {self.expiration_date}"

    def clean(self):
        super().clean()
        if (
            self.received_at
            and self.expiration_date
            and self.expiration_date < self.received_at
        ):
            raise ValidationError(
                {"expiration_date": "Expiration date must be on or after the received date."}
            )
