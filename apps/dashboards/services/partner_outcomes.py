"""Partner outcomes — read-only aggregation, partner-scoped.

Story 6.2.

The single entry point is :func:`build`; it returns a dict with
``rows`` and ``aggregate``. The view layer is responsible for choosing
the ``partner_id`` — always from ``request.user.partner_id``, never
from the URL or query string. Filtering by ``partner_id`` happens at
the queryset level so a malicious caller cannot exfiltrate rows from
another partner by any means.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import timedelta

from django.db.models import Avg, OuterRef, Subquery
from django.utils import timezone


@dataclass(frozen=True)
class OutcomeRow:
    member_id: int
    full_name: str
    suburb: str
    status: str
    enrolment_date: str
    last_delivery: str | None
    avg_rating: float | None


def _base_queryset(partner_id: int):
    """All members referred by ``partner_id``.

    Uses ``all_objects`` so soft-deleted users still appear (their
    ``deleted_at`` flips ``status`` to ``inactive`` — see
    :func:`_status_for`). Filter is anchored on ``partner_id`` first;
    every downstream query inherits this scoping.
    """
    from apps.accounts.models import User

    return User.all_objects.filter(role="member", partner_id=partner_id)


def _status_for(user_row: dict) -> str:
    """Derive the textual status shown in the table.

    A member is ``active`` iff ``is_active=1`` AND ``deleted_at`` is
    NULL. The acceptance criteria intentionally collapse every other
    case into ``inactive`` — no extra states (``paused``, ``churned``)
    are invented here.
    """
    if user_row["is_active"] and user_row["deleted_at"] is None:
        return "active"
    return "inactive"


def _rows(partner_id: int) -> list[OutcomeRow]:
    from apps.accounts.models import Address
    from apps.delivery.models import Delivery, DeliveryFeedback

    last_delivery_sq = (
        Delivery.objects.filter(member_id=OuterRef("pk"))
        .order_by("-delivered_time")
        .values("delivered_time")[:1]
    )
    avg_rating_sq = (
        DeliveryFeedback.objects.filter(
            delivery__member_id=OuterRef("pk")
        )
        .values("delivery__member_id")
        .annotate(avg=Avg("rating"))
        .values("avg")[:1]
    )
    qs = (
        _base_queryset(partner_id)
        .annotate(
            last_delivery=Subquery(last_delivery_sq),
            avg_rating=Subquery(avg_rating_sq),
        )
        .order_by("full_name")
        .values(
            "id",
            "full_name",
            "is_active",
            "deleted_at",
            "created_at",
            "last_delivery",
            "avg_rating",
        )
    )
    user_rows = list(qs)
    # Suburb: a separate small query keeps the row SQL readable. We pick
    # the first address per member by ``id`` so the choice is
    # deterministic across requests.
    user_ids = [u["id"] for u in user_rows]
    suburb_pairs = (
        Address.objects.filter(user_id__in=user_ids)
        .order_by("user_id", "id")
        .values_list("user_id", "city__name")
    )
    suburbs: dict[int, str] = {}
    for uid, city_name in suburb_pairs:
        # ``dict.setdefault`` keeps the first hit for each user.
        suburbs.setdefault(uid, city_name or "")

    rows: list[OutcomeRow] = []
    for u in user_rows:
        rows.append(
            OutcomeRow(
                member_id=u["id"],
                full_name=u["full_name"],
                suburb=suburbs.get(u["id"], ""),
                status=_status_for(u),
                enrolment_date=(
                    u["created_at"].date().isoformat()
                    if u["created_at"]
                    else ""
                ),
                last_delivery=(
                    u["last_delivery"].date().isoformat()
                    if u["last_delivery"]
                    else None
                ),
                avg_rating=(
                    round(float(u["avg_rating"]), 1)
                    if u["avg_rating"] is not None
                    else None
                ),
            )
        )
    return rows


def _aggregate(partner_id: int) -> dict:
    qs = _base_queryset(partner_id)
    total = qs.count()
    active = qs.filter(is_active=True, deleted_at__isnull=True).count()
    # 90-day retention: of members enrolled on/before T-90, % still
    # active. ``Australia/Melbourne`` is the project tz so
    # ``timezone.localdate()`` already respects it.
    cutoff = timezone.localdate() - timedelta(days=90)
    eligible = qs.filter(created_at__date__lte=cutoff)
    denom = eligible.count()
    if denom == 0:
        retention = None
    else:
        retained = eligible.filter(
            is_active=True, deleted_at__isnull=True
        ).count()
        retention = round(retained / denom * 100, 1)
    return {
        "total_referred": total,
        "currently_active": active,
        "retention_pct_90d": retention,
    }


def build(partner_id: int) -> dict:
    """Build the full payload for a single partner.

    Always pass ``request.user.partner_id`` from the view — never an
    untrusted integer from the URL or query string.
    """
    return {
        "rows": [asdict(r) for r in _rows(partner_id)],
        "aggregate": _aggregate(partner_id),
    }
