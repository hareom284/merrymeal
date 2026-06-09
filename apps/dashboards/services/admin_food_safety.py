"""Admin food-safety browser (Story 12.12).

Backs the ``/admin/food_safety/`` page so admins can audit every
check across every kitchen without piecing it together from the
kitchen-staff capture screen.

The filter shape mirrors what the user pasted from the Django
auto-admin URL (``?kitchen__id__exact=1``): kitchen + result + date
range. Add-new lives in
``apps.food_safety.services.checks.record_check`` so the admin's
create form is just a thin wrapper around the existing kitchen-staff
service — no duplicate validation, no separate audit path.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date as _date
from datetime import datetime, time
from typing import Any

from django.core.paginator import Paginator
from django.db.models import QuerySet
from django.utils import timezone

from apps.food_safety.models import FoodSafetyCheck

# Page size for the audit table — same default as members.
PAGE_SIZE = 25


@dataclass(frozen=True)
class FsCheckFilters:
    kitchen_id: int | None = None
    result: str = ""  # "" | "pass" | "fail"
    date_from: _date | None = None
    date_to: _date | None = None


def _base_queryset() -> QuerySet[FoodSafetyCheck]:
    return FoodSafetyCheck.objects.select_related("kitchen", "checked_by")


def _to_aware_start(d: _date):
    """Combine a date with 00:00 in the current TZ for datetime__gte."""
    return timezone.make_aware(datetime.combine(d, time.min))


def _to_aware_end(d: _date):
    """Combine a date with 23:59:59.999 in the current TZ for __lte."""
    return timezone.make_aware(datetime.combine(d, time.max))


def search_checks(filters: FsCheckFilters, page: int = 1) -> dict[str, Any]:
    """Return ``{"page": Page, "filters": FsCheckFilters, "total": int}``.

    Ordered newest-first (admins are usually checking "what just
    happened?"), tie-broken by id so pagination stays deterministic
    when many checks share the same checked_at second.
    """
    qs = _base_queryset()

    if filters.kitchen_id:
        qs = qs.filter(kitchen_id=filters.kitchen_id)
    if filters.result in {"pass", "fail"}:
        qs = qs.filter(result=filters.result)
    if filters.date_from:
        qs = qs.filter(checked_at__gte=_to_aware_start(filters.date_from))
    if filters.date_to:
        qs = qs.filter(checked_at__lte=_to_aware_end(filters.date_to))

    qs = qs.order_by("-checked_at", "-id")

    paginator = Paginator(qs, PAGE_SIZE)
    page_obj = paginator.get_page(page)

    return {
        "page": page_obj,
        "filters": filters,
        "total": paginator.count,
    }
