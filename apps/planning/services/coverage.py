"""Diet-coverage warning service (Story 3.6).

For a given MealPlan, return per-DietPreference counts of members served
fresh by that plan whose declared diet the planned meal does NOT cover.

v1 compatibility = pure tag match: a meal is compatible with diet X iff
``meal.diets.filter(pk=X.pk).exists()``. No nutritional analysis, no
ingredient introspection.

Weekend plans always return an empty warning dict — those members all get
pre-batched frozen meals regardless of diet, and surfacing the warning
would be noise (per the story spec).
"""
from __future__ import annotations

from collections import Counter

from apps.accounts.models import User
from apps.planning.services.assignment import assign_meal_type
from apps.planning.services.exceptions import AddressMissingError


def _candidate_members(meal_plan):
    """Yield members served *fresh* by this plan's kitchen on the plan's date.

    Members with no usable address are silently skipped — they cannot be
    diet-warned on because we don't know if they're inside the radius.
    """
    candidates = (
        User.objects.filter(role="member", is_active=True)
        .prefetch_related("diet_preferences", "addresses")
    )
    for member in candidates:
        try:
            outcome = assign_meal_type(
                member, meal_plan.kitchen, meal_plan.service_date
            )
        except AddressMissingError:
            continue
        if outcome == "fresh":
            yield member


def diet_warnings(meal_plan) -> dict:
    """Return ``{DietPreference: count}`` for diets the meal does not cover.

    Empty dict when no candidate members hold any uncovered diet.
    """
    covered_ids = set(meal_plan.meal.diets.values_list("id", flat=True))
    counts: Counter = Counter()
    for member in _candidate_members(meal_plan):
        for diet in member.diet_preferences.all():
            if diet.id not in covered_ids:
                counts[diet] += 1
    return dict(counts)


def acknowledge(meal_plan, user) -> None:
    """Mark this plan's diet warnings as acknowledged by ``user``.

    The badge UI then renders in muted grey instead of yellow. The
    acknowledgement is cleared automatically when the cell's meal is
    swapped (see ``apps.planning.services.planner.upsert_cell``).
    """
    meal_plan.warnings_acknowledged_by = user
    meal_plan.save(update_fields=["warnings_acknowledged_by"])
