"""Admin members directory (Story 12.11).

Read-only search/list/detail for members. Filtering is intentionally
simple — name/email substring + active/inactive + partner — because the
member set scales to thousands, not millions. When the table outgrows
that, swap the ``icontains`` for a Postgres trigram or a search vector
without changing the view shape.

Returns plain dicts / model instances so the template needs no extra
massaging.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from django.core.paginator import Paginator
from django.db.models import Q, QuerySet

from apps.accounts.models import User

# Page size for the directory table — small enough that the page renders
# fast on a phone, big enough to scroll without flipping pages.
PAGE_SIZE = 25


@dataclass(frozen=True)
class MemberSearchFilters:
    q: str = ""
    status: str = ""  # "" | "active" | "inactive"
    partner_id: int | None = None


def _base_queryset() -> QuerySet[User]:
    return (
        User.objects.filter(role="member")
        .select_related("partner")
        .prefetch_related("addresses__city")
    )


def search_members(filters: MemberSearchFilters, page: int = 1) -> dict[str, Any]:
    """Return ``{"page": Page, "filters": MemberSearchFilters, "total": int}``.

    ``page`` is a Django ``Page`` so the template can ``.has_next``,
    ``.has_previous``, etc. The ``filters`` echo is so the template can
    re-render the search inputs with the active values without the view
    having to pass them twice.
    """
    qs = _base_queryset()

    q = (filters.q or "").strip()
    if q:
        qs = qs.filter(Q(full_name__icontains=q) | Q(email__icontains=q))

    if filters.status == "active":
        qs = qs.filter(is_active=True)
    elif filters.status == "inactive":
        qs = qs.filter(is_active=False)

    if filters.partner_id:
        qs = qs.filter(partner_id=filters.partner_id)

    qs = qs.order_by("full_name", "id")

    paginator = Paginator(qs, PAGE_SIZE)
    page_obj = paginator.get_page(page)

    return {
        "page": page_obj,
        "filters": filters,
        "total": paginator.count,
    }


def get_member_detail(pk: int) -> dict[str, Any] | None:
    """Return the full member context, or ``None`` if no member with
    that PK exists. Returns dicts/instances directly — the template
    reads ``member.addresses.all`` etc."""
    member = (
        User.objects.filter(pk=pk, role="member")
        .select_related("partner")
        .prefetch_related(
            "addresses__city",
            "allergies",
            "diet_preferences",
            "caregiver_links_as_member__caregiver",
        )
        .first()
    )
    if member is None:
        return None

    # Recent deliveries (last 10), most-recent first. Lazy import keeps
    # the dashboards layer free of a Delivery FK at module load.
    from apps.delivery.models import Delivery
    deliveries = list(
        Delivery.objects.filter(member=member)
        .select_related("meal_plan__meal", "volunteer")
        .order_by("-scheduled_date", "-id")[:10]
    )

    return {
        "member": member,
        "addresses": list(member.addresses.all()),
        "allergies": list(member.allergies.all()),
        "diet_preferences": list(member.diet_preferences.all()),
        "caregiver_links": list(member.caregiver_links_as_member.all()),
        "recent_deliveries": deliveries,
    }
