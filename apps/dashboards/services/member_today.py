"""Today's-meal card service for the member dashboard.

Story 3.4 (member today card). This file is created defensively as a
dependency of Story 3.8 (caregiver multi-member view) because the
parallel 3.4 branch has not merged yet. Keep the public API
(`get_today_card(member) -> dict`) stable so the 3.4 branch can drop
its template fragment on top without code changes.
"""
from __future__ import annotations

import datetime as dt
from typing import Any

from django.utils import timezone

from apps.core.geo import haversine_km
from apps.planning.models import MealPlan


def _empty_card(today: dt.date, next_plan_date: dt.date | None) -> dict[str, Any]:
    return {
        "has_meal": False,
        "service_date": today,
        "next_plan_date": next_plan_date,
        "meal_name": "",
        "meal_description": "",
        "ingredient_names": [],
        "allergens": [],
        "delivery_status_label": "No meal scheduled",
    }


def _nearest_kitchen_for(member, plans_qs):
    """Pick the MealPlan whose kitchen is closest to (and within range of)
    the member's first usable address. Returns the chosen plan or None.

    A kitchen is "usable" when both the member address and the kitchen
    have lat/lng and the great-circle distance is <= the kitchen's
    `service_radius_km`.
    """
    address = (
        member.addresses
        .exclude(latitude__isnull=True)
        .exclude(longitude__isnull=True)
        .first()
    )
    if address is None:
        return None

    best_plan = None
    best_distance = None
    for plan in plans_qs:
        k = plan.kitchen
        if k.latitude is None or k.longitude is None:
            continue
        distance = haversine_km(
            float(address.latitude), float(address.longitude),
            float(k.latitude), float(k.longitude),
        )
        if distance > float(k.service_radius_km):
            continue
        if best_distance is None or distance < best_distance:
            best_plan = plan
            best_distance = distance
    return best_plan


def get_today_card(member, today: dt.date | None = None) -> dict[str, Any]:
    """Return a dict describing what `member` is getting today.

    Shape (stable):
      {
        "has_meal": bool,
        "service_date": date,
        "next_plan_date": date | None,
        "meal_name": str,
        "meal_description": str,
        "ingredient_names": list[str],
        "allergens": list[Allergy],
        "delivery_status_label": str,
      }
    """
    today = today or timezone.localdate()

    todays_plans = (
        MealPlan.objects
        .filter(service_date=today)
        .select_related("kitchen", "meal")
        .prefetch_related("meal__ingredients", "meal__ingredients__contains_allergens")
    )
    plan = _nearest_kitchen_for(member, todays_plans)

    if plan is None:
        next_plan = (
            MealPlan.objects
            .filter(service_date__gt=today)
            .order_by("service_date")
            .values_list("service_date", flat=True)
            .first()
        )
        return _empty_card(today, next_plan)

    meal = plan.meal
    ingredient_names = [i.name for i in meal.ingredients.all()]

    member_allergy_ids = set(
        member.allergies.values_list("id", flat=True)
    )
    flagged: list = []
    seen: set = set()
    for ingredient in meal.ingredients.all():
        for allergen in ingredient.contains_allergens.all():
            if allergen.id in member_allergy_ids and allergen.id not in seen:
                flagged.append(allergen)
                seen.add(allergen.id)

    return {
        "has_meal": True,
        "service_date": today,
        "next_plan_date": None,
        "meal_name": meal.name,
        "meal_description": meal.description or "",
        "ingredient_names": ingredient_names,
        "allergens": flagged,
        "delivery_status_label": f"Planned for {today.strftime('%a %d %b')}",
    }
