"""Admin volunteers directory (Story 12.13).

Same shape as :mod:`apps.dashboards.services.admin_members` —
paginated search, active/inactive filter — but scoped to
``role=volunteer``. Detail surfaces the availability slot grid and
delivery history so an admin can see at a glance whether a volunteer
is reliable.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from django.core.paginator import Paginator
from django.db.models import Q, QuerySet

from apps.accounts.models import User

PAGE_SIZE = 25


@dataclass(frozen=True)
class VolunteerSearchFilters:
    q: str = ""
    status: str = ""  # "" | "active" | "inactive"


def _base_queryset() -> QuerySet[User]:
    return User.objects.filter(role="volunteer")


def search_volunteers(
    filters: VolunteerSearchFilters, page: int = 1
) -> dict[str, Any]:
    qs = _base_queryset()
    q = (filters.q or "").strip()
    if q:
        qs = qs.filter(Q(full_name__icontains=q) | Q(email__icontains=q))
    if filters.status == "active":
        qs = qs.filter(is_active=True)
    elif filters.status == "inactive":
        qs = qs.filter(is_active=False)
    qs = qs.order_by("full_name", "id")

    paginator = Paginator(qs, PAGE_SIZE)
    page_obj = paginator.get_page(page)
    return {"page": page_obj, "filters": filters, "total": paginator.count}


# Stable ordering for the availability matrix the detail page renders.
# Templates iterate ``DAY_ORDER`` and look up
# ``availability_by_day_phrase[day]`` so the grid is dense even when a
# volunteer has gaps.
DAY_ORDER = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
PHRASE_ORDER = ["morning", "afternoon", "evening"]


def get_volunteer_detail(pk: int) -> dict[str, Any] | None:
    volunteer = (
        User.objects.filter(pk=pk, role="volunteer")
        .prefetch_related("availabilities")
        .first()
    )
    if volunteer is None:
        return None

    availability_set: set[tuple[str, str]] = {
        (a.day_of_week, a.day_phrase) for a in volunteer.availabilities.all()
    }
    # Flat per-row dicts so the template can iterate without a custom
    # dict-lookup filter (Django can't do ``matrix[day][phrase]`` with a
    # variable key in its built-in syntax). Each entry's ``cells`` is a
    # list of ``{"phrase": "morning", "active": bool}`` rows the
    # template reads via dot-access.
    availability_rows = [
        {
            "day": day,
            "cells": [
                {"phrase": phrase, "active": (day, phrase) in availability_set}
                for phrase in PHRASE_ORDER
            ],
        }
        for day in DAY_ORDER
    ]

    from apps.delivery.models import Delivery
    recent_deliveries = list(
        Delivery.objects.filter(volunteer=volunteer)
        .select_related("member", "meal_plan__meal")
        .order_by("-scheduled_date", "-id")[:10]
    )

    # Quick reliability snapshot: out of recent deliveries, how many
    # actually completed? Templates show "8/10" — a simple ratio admins
    # can scan without doing the math themselves.
    completed = sum(1 for d in recent_deliveries if d.status == Delivery.STATUS_DELIVERED)

    return {
        "volunteer": volunteer,
        "availability_rows": availability_rows,
        "phrase_order": PHRASE_ORDER,
        "recent_deliveries": recent_deliveries,
        "recent_completed": completed,
        "recent_total": len(recent_deliveries),
    }
