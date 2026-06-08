from datetime import date
from decimal import Decimal

from django.db import transaction

from apps.kitchens.models import Ingredient, IngredientBatch, Kitchen


@transaction.atomic
def receive_batch(
    *,
    user,
    kitchen: Kitchen,
    ingredient: Ingredient,
    quantity: Decimal,
    expiration_date: date,
    received_at: date | None = None,
    lot_number: str | None = None,
) -> IngredientBatch:
    """Record an incoming stock batch.

    Args:
        user: the staff member performing the action (kept for Sprint 05 audit).
        kitchen, ingredient, quantity, expiration_date: required fields.
        received_at: defaults to today.
        lot_number: optional supplier-provided lot.

    Raises:
        ValidationError if any field is invalid.
    """
    batch = IngredientBatch(
        kitchen=kitchen,
        ingredient=ingredient,
        quantity=quantity,
        expiration_date=expiration_date,
        received_at=received_at or date.today(),
        lot_number=lot_number or None,
    )
    batch.full_clean()
    batch.save()
    return batch
