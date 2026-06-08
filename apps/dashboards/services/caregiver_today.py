"""Caregiver-side today summary.

Story 3.8 — Caregiver multi-member view.

Wraps Story 3.4's `get_today_card(member)` so each linked member yields
one row in the caregiver list view.
"""
from __future__ import annotations

from typing import Any

from apps.accounts.models import User
from apps.dashboards.services.member_today import get_today_card


def linked_members(caregiver: User):
    """Return the members `caregiver` is linked to via `member_caregivers`.

    Uses the `caregiver_links_as_caregiver` reverse manager (Epic 01's
    chosen related_name on the through model `CaregiverLink`).
    """
    return (
        User.objects
        .filter(caregiver_links_as_member__caregiver=caregiver)
        .order_by("full_name")
        .distinct()
    )


def get_caregiver_summary(caregiver: User) -> list[dict[str, Any]]:
    """Return one summary dict per linked member.

    Shape:
      [
        {"member": User, "card": <today_card>, "allergen_label": str},
        ...
      ]
    """
    summaries: list[dict[str, Any]] = []
    for member in linked_members(caregiver):
        card = get_today_card(member)
        allergens = card.get("allergens") or []
        allergen_label = (
            "⚠ Contains " + ", ".join(a.name for a in allergens)
            if allergens else ""
        )
        summaries.append({
            "member": member,
            "card": card,
            "allergen_label": allergen_label,
        })
    return summaries
