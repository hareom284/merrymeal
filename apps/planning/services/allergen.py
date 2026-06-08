"""Allergen intersection between a meal's ingredients and a member's
declared allergies.

Pure — no DB writes. Used by Story 3.4's today-card service and Story 3.8's
caregiver row to flag dangerous meals before serve.
"""

from __future__ import annotations


def meal_allergens_for_member(meal, member) -> list:
    """Return the de-duplicated intersection of the meal's ingredient
    allergens and the member's declared allergies, as a ``list[Allergy]``.

    One query for the member's allergy ids, one for the meal's ingredients
    (with their allergens prefetched). Order is the order ingredients are
    iterated — stable enough for templates; callers that need alphabetical
    output should sort.
    """
    member_allergy_ids = set(member.allergies.values_list("id", flat=True))
    if not member_allergy_ids:
        return []

    seen: set[int] = set()
    matched: list = []
    qs = meal.ingredients.prefetch_related("contains_allergens")
    for ing in qs:
        for a in ing.contains_allergens.all():
            if a.id in member_allergy_ids and a.id not in seen:
                seen.add(a.id)
                matched.append(a)
    return matched
