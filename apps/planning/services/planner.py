"""Planner service — upsert a single (kitchen, service_date) MealPlan row.

This is the write-side of the Story 3.3 admin weekly-planner UI.

The fresh/frozen choice set here is the *kitchen-wide* default. The
per-member 10 km radius decision (`apps.planning.services.assign_meal_type`)
is applied later, at delivery generation (Epic 04).
"""

from __future__ import annotations

import datetime as dt

from apps.planning.models import MealPlan

DAY_KEYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]


def upsert_cell(
    *,
    kitchen,
    meal,
    service_date: dt.date,
    planned_quantity: int,
    published_by,
) -> MealPlan:
    """Create or update the MealPlan for (kitchen, service_date).

    Sets ``day_of_week`` from the date and ``meal_type`` to ``'frozen'`` on
    Sat/Sun else ``'fresh'``. The per-member 10 km decision is applied
    later, at delivery generation (Epic 04). See
    :func:`apps.planning.services.assign_meal_type` for the per-member rule.
    """
    weekday = service_date.weekday()
    plan, _ = MealPlan.objects.update_or_create(
        kitchen=kitchen,
        service_date=service_date,
        defaults={
            "meal": meal,
            "day_of_week": DAY_KEYS[weekday],
            "meal_type": "frozen" if weekday in (5, 6) else "fresh",
            "planned_quantity": planned_quantity,
            "published_by": published_by,
            # Editing the cell invalidates any prior diet-coverage ack
            # (the new meal has a different compatibility profile).
            "warnings_acknowledged_by": None,
        },
    )
    return plan
