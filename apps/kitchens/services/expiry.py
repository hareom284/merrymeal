from datetime import timedelta

from django.db.models import QuerySet
from django.utils import timezone

from apps.kitchens.models import IngredientBatch


def find_expiring_batches(kitchen, *, within_days: int = 3) -> QuerySet[IngredientBatch]:
    """Batches in the given kitchen with quantity remaining whose expiry is
    today or within `within_days` days. Ordered by ingredient_id, expiration_date."""
    cutoff = timezone.localdate() + timedelta(days=within_days)
    return (
        IngredientBatch.objects
        .filter(
            kitchen=kitchen,
            expiration_date__lte=cutoff,
            quantity__gt=0,
        )
        .select_related("ingredient")
        .order_by("ingredient_id", "expiration_date")
    )
