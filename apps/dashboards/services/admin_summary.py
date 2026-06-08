"""Story 6.1 — admin home dashboard aggregation.

Pure read-only queries; no side effects. The view layer maps each
``Card`` to its template severity colour.

Five cards are returned in a fixed order so the template iterates a
uniform shape. Thresholds live here (single source of truth) so future
tweaks do not touch the HTML.

Time zone: ``timezone.localdate()`` is bound to ``Australia/Melbourne``
through ``settings.TIME_ZONE``; do **not** use naive ``datetime.now()``
when filtering ``DateField`` columns.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Literal

from django.urls import NoReverseMatch, reverse
from django.utils import timezone

Severity = Literal["green", "yellow", "red"]


@dataclass(frozen=True)
class Card:
    title: str
    count: int
    link: str
    severity: Severity
    threshold: int


# Per-card thresholds. Adjust here; do not hard-code in templates.
_THRESHOLDS = {
    "pending_apps": 10,
    "expiring_stock": 5,
    "failed_deliveries": 1,
    "unassigned_deliveries": 3,
    "fs_failures": 1,
}


def severity(count: int, *, threshold: int) -> Severity:
    """Traffic-light helper.

    - ``green`` when nothing needs attention.
    - ``yellow`` when there is some activity but below the alarm bar.
    - ``red`` once the count meets or exceeds the threshold.
    """
    if count == 0:
        return "green"
    if count >= threshold:
        return "red"
    return "yellow"


# ---- per-card count helpers ----


def _count_pending_applications() -> int:
    # Spec uses ``status="submitted"`` (Epic 01). The Application model
    # exposes this as ``STATUS_SUBMITTED``.
    from apps.accounts.models import Application

    return Application.objects.filter(status=Application.STATUS_SUBMITTED).count()


def _count_expiring_stock() -> int:
    # Spec refers to ``ingredient_batches.expiration_date <= today + 3``.
    from apps.kitchens.models import IngredientBatch

    today = timezone.localdate()
    return IngredientBatch.objects.filter(
        expiration_date__lte=today + timedelta(days=3),
    ).count()


def _count_failed_deliveries_today() -> int:
    # Spec references ``apps.deliveries``; this codebase ships the app as
    # ``apps.delivery`` with the same ``Delivery`` model.
    from apps.delivery.models import Delivery

    return Delivery.objects.filter(
        status=Delivery.STATUS_FAILED,
        scheduled_date=timezone.localdate(),
    ).count()


def _count_unassigned_deliveries_today() -> int:
    # NOTE: Story 4.7 envisaged a nullable ``volunteer_id`` to model the
    # overflow queue. The current Delivery schema has volunteer as
    # PROTECT/non-null (see ``apps/delivery/models/deliveries.py``); the
    # closest available signal is "scheduled today but still pending
    # dispatch" — deliveries the route board has not yet moved to
    # ``out_for_delivery``. When the overflow queue lands, swap this to a
    # ``volunteer_id__isnull=True`` filter.
    from apps.delivery.models import Delivery

    return Delivery.objects.filter(
        status=Delivery.STATUS_PENDING,
        scheduled_date=timezone.localdate(),
        route__isnull=True,
    ).count()


def _count_fs_failures_24h() -> int:
    from apps.food_safety.models import FoodSafetyCheck

    since = timezone.now() - timedelta(hours=24)
    return FoodSafetyCheck.objects.filter(
        result=FoodSafetyCheck.Result.FAIL,
        checked_at__gte=since,
    ).count()


# ---- public ----


def build() -> list[Card]:
    """Aggregate every "needs attention" metric into a flat list.

    Five small ``.count()`` queries; do not coerce into a single query —
    readability wins on an admin-only page.
    """
    # Each spec is (title, counter, named-route-or-fallback, threshold).
    # Named routes that have not been built yet degrade to ``link="#"``
    # via the NoReverseMatch guard below — a follow-up story replaces
    # the placeholder once the dedicated filtered-list view lands.
    specs = [
        (
            "Pending applications",
            _count_pending_applications,
            "dashboards:admin_applications",
            _THRESHOLDS["pending_apps"],
        ),
        (
            "Expiring stock",
            _count_expiring_stock,
            "dashboards:expiring_stock",
            _THRESHOLDS["expiring_stock"],
        ),
        (
            "Failed deliveries today",
            _count_failed_deliveries_today,
            "dashboards:failed_deliveries_today",
            _THRESHOLDS["failed_deliveries"],
        ),
        (
            "Unassigned deliveries today",
            _count_unassigned_deliveries_today,
            "dashboards:unassigned_deliveries_today",
            _THRESHOLDS["unassigned_deliveries"],
        ),
        (
            "Recent food-safety failures",
            _count_fs_failures_24h,
            "dashboards:fs_failures_recent",
            _THRESHOLDS["fs_failures"],
        ),
    ]

    cards: list[Card] = []
    for title, counter, route_name, threshold in specs:
        try:
            link = reverse(route_name)
        except NoReverseMatch:
            link = "#"
        count = counter()
        cards.append(
            Card(
                title=title,
                count=count,
                link=link,
                severity=severity(count, threshold=threshold),
                threshold=threshold,
            )
        )
    return cards
