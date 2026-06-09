"""Admin partners directory (Story 12.15).

Same shape as the other admin CRUDs: paginated search +
type filter + detail builder. Detail aggregates from User
(members affiliated via Partner) and Application (referrals
submitted via Partner) so an admin can see one partner's full
footprint without leaving the page.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from django.core.paginator import Paginator
from django.db.models import QuerySet

from apps.partners.models import Partner

PAGE_SIZE = 25


@dataclass(frozen=True)
class PartnerSearchFilters:
    q: str = ""
    type: str = ""  # "" | "charity" | "restaurant" | "supplier" | "corporate"


def _base_queryset() -> QuerySet[Partner]:
    return Partner.objects.all()


def search_partners(filters: PartnerSearchFilters, page: int = 1) -> dict[str, Any]:
    qs = _base_queryset()
    q = (filters.q or "").strip()
    if q:
        qs = qs.filter(legal_name__icontains=q)
    if filters.type in {"charity", "restaurant", "supplier", "corporate"}:
        qs = qs.filter(type=filters.type)
    qs = qs.order_by("legal_name", "id")
    paginator = Paginator(qs, PAGE_SIZE)
    return {
        "page": paginator.get_page(page),
        "filters": filters,
        "total": paginator.count,
    }


def get_partner_detail(pk: int) -> dict[str, Any] | None:
    """Return everything the detail page renders, or ``None`` if no
    partner with that PK exists. Aggregates from the partner's
    referrals + affiliated members so the admin sees impact at a glance."""
    from apps.accounts.models import Application, User

    partner = Partner.objects.filter(pk=pk).first()
    if partner is None:
        return None

    affiliated_members = list(
        User.objects.filter(role="member", partner=partner)
        .order_by("-created_at", "-id")[:10]
    )
    affiliated_members_total = User.objects.filter(
        role="member", partner=partner
    ).count()

    referrals = list(
        Application.objects.filter(partner=partner)
        .order_by("-created_at", "-id")[:10]
    )
    referrals_total = Application.objects.filter(partner=partner).count()

    return {
        "partner": partner,
        "affiliated_members": affiliated_members,
        "affiliated_members_total": affiliated_members_total,
        "referrals": referrals,
        "referrals_total": referrals_total,
    }
