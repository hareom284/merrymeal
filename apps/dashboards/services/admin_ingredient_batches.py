"""Admin ingredient-batch browser (Story 12.16).

The kitchen-staff ``/kitchen/`` page lets staff log incoming batches one
by one; this service powers the admin's cross-kitchen view —
list/filter every batch in the system with one search.

Filter shape mirrors what an admin asks at a glance:
  * which kitchen
  * which ingredient
  * how soon does it expire (or has it already expired)

Add-new flows through ``apps.kitchens.services.stock.receive_batch`` so
the admin's create path and the kitchen-staff create path share the
same audit-logged write — no duplicate validation, no second insert
codepath.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

from django.core.paginator import Paginator
from django.db.models import QuerySet
from django.utils import timezone

from apps.kitchens.models import IngredientBatch

PAGE_SIZE = 25


@dataclass(frozen=True)
class BatchSearchFilters:
    kitchen_id: int | None = None
    ingredient_id: int | None = None
    expiring_within_days: int | None = None  # ``<=`` today + N
    expired_only: bool = False


def _base_queryset() -> QuerySet[IngredientBatch]:
    return IngredientBatch.objects.select_related("kitchen", "ingredient")


def search_batches(filters: BatchSearchFilters, page: int = 1) -> dict[str, Any]:
    qs = _base_queryset()
    today = timezone.localdate()

    if filters.kitchen_id:
        qs = qs.filter(kitchen_id=filters.kitchen_id)
    if filters.ingredient_id:
        qs = qs.filter(ingredient_id=filters.ingredient_id)
    if filters.expired_only:
        qs = qs.filter(expiration_date__lt=today)
    elif filters.expiring_within_days is not None:
        cutoff = today + timedelta(days=filters.expiring_within_days)
        qs = qs.filter(expiration_date__lte=cutoff)

    # Soonest-expiring first so the most urgent batches surface at the
    # top — same ordering the kitchen attention card uses.
    qs = qs.order_by("expiration_date", "id")

    paginator = Paginator(qs, PAGE_SIZE)
    return {
        "page": paginator.get_page(page),
        "filters": filters,
        "total": paginator.count,
        "today": today,
    }


def days_until_expiry(batch: IngredientBatch, today: date | None = None) -> int:
    """Negative when already expired, 0 if today, positive if future."""
    return (batch.expiration_date - (today or timezone.localdate())).days
