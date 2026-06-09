"""Standalone weekly menu page composer (Story 12.5).

The dashboard already renders a 5-day strip via
``apps.dashboards.services.member_dashboard._get_week_menu``. This
service is its longer cousin: 7 days, full meal name + ingredients +
member-specific allergen warnings + the kitchen the meal will come
from. Used by the dedicated ``/menu/`` page so a member can plan their
week from a single screen.

Why a separate service: the dashboard strip is intentionally terse
(small card, no ingredient list, no allergen pills). Reusing it here
would have meant either bloating the dashboard's shape with optional
fields or post-processing the same query twice. A focused builder is
cheaper to evolve.
"""
from __future__ import annotations

import datetime as dt
from typing import Any

from django.utils import timezone

from apps.dashboards.services.member_today import _nearest_kitchen_for
from apps.planning.models import MealPlan

WEEK_DAY_LABELS = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]


def _day_state(day: dt.date, today: dt.date) -> str:
    if day < today:
        return "done"
    if day == today:
        return "today"
    return "upcoming"


def build_weekly_menu_context(member, today: dt.date | None = None) -> dict[str, Any]:
    """Return ``{"today": date, "days": [...]}`` for the member's week.

    ``days`` is exactly 7 entries (Mon–Sun of the ISO week containing
    ``today``). Each entry:
      {
        "date": date,
        "weekday": "MON"|"TUE"|...,
        "state": "done"|"today"|"upcoming",
        "meal_name": str,                # "—" when no plan
        "meal_description": str,
        "ingredient_names": list[str],
        "allergens": list[Allergy],      # member-specific flags
        "kitchen_name": str | None,
      }
    """
    today = today or timezone.localdate()
    monday = today - dt.timedelta(days=today.weekday())
    week_dates = [monday + dt.timedelta(days=i) for i in range(7)]

    plans_qs = (
        MealPlan.objects.filter(service_date__in=week_dates)
        .select_related("kitchen", "meal")
        .prefetch_related(
            "meal__ingredients",
            "meal__ingredients__contains_allergens",
        )
    )
    plans_by_date: dict[dt.date, list[MealPlan]] = {}
    for plan in plans_qs:
        plans_by_date.setdefault(plan.service_date, []).append(plan)

    member_allergy_ids = set(member.allergies.values_list("id", flat=True))

    days: list[dict[str, Any]] = []
    for day in week_dates:
        candidates = plans_by_date.get(day, [])
        plan = _nearest_kitchen_for(member, candidates) if candidates else None

        if plan is None:
            days.append({
                "date": day,
                "weekday": WEEK_DAY_LABELS[day.weekday()],
                "state": _day_state(day, today),
                "meal_name": "—",
                "meal_description": "",
                "ingredient_names": [],
                "allergens": [],
                "kitchen_name": None,
            })
            continue

        ingredient_names = [i.name for i in plan.meal.ingredients.all()]

        flagged = []
        seen: set[int] = set()
        for ingredient in plan.meal.ingredients.all():
            for allergen in ingredient.contains_allergens.all():
                if allergen.id in member_allergy_ids and allergen.id not in seen:
                    flagged.append(allergen)
                    seen.add(allergen.id)

        days.append({
            "date": day,
            "weekday": WEEK_DAY_LABELS[day.weekday()],
            "state": _day_state(day, today),
            "meal_name": plan.meal.name,
            "meal_description": plan.meal.description or "",
            "ingredient_names": ingredient_names,
            "allergens": flagged,
            "kitchen_name": plan.kitchen.name if plan.kitchen else None,
        })

    return {"today": today, "days": days}
