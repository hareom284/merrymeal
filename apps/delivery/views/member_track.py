"""Member track-delivery page (Story 12.7).

Full-page version of the live-tracking partial Story 4.12 ships into
the dashboard. Adds a Mapbox static-image map and the kitchen-fallback
location logic so the page still renders meaningfully before the
volunteer has reported any GPS coordinates.
"""
from __future__ import annotations

import datetime as dt

from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils import timezone

from apps.core.decorators import role_required
from apps.delivery.models import Delivery
from apps.delivery.services.map_snapshot import static_map_url
from apps.delivery.services.tracking import get_tracking_context


def _pick_today_delivery(member, today: dt.date) -> Delivery | None:
    """Same precedence as the dashboard: out_for_delivery > pending >
    delivered > failed. Returns ``None`` when nothing scheduled."""
    qs = (
        Delivery.objects
        .filter(member=member, scheduled_date=today)
        .select_related("volunteer", "meal_plan__meal", "meal_plan__kitchen")
    )
    by_priority = {
        Delivery.STATUS_OUT_FOR_DELIVERY: 0,
        Delivery.STATUS_PENDING: 1,
        Delivery.STATUS_DELIVERED: 2,
        Delivery.STATUS_FAILED: 3,
    }
    rows = sorted(qs, key=lambda d: by_priority.get(d.status, 9))
    return rows[0] if rows else None


def _map_coords(delivery: Delivery) -> tuple[float | None, float | None]:
    """Volunteer's last known GPS if recorded; otherwise the serving
    kitchen's coordinates. ``(None, None)`` if neither is available —
    the template falls back to a placeholder block."""
    if delivery.latitude is not None and delivery.longitude is not None:
        return float(delivery.latitude), float(delivery.longitude)
    kitchen = delivery.meal_plan.kitchen
    if kitchen.latitude is not None and kitchen.longitude is not None:
        return float(kitchen.latitude), float(kitchen.longitude)
    return None, None


@login_required
@role_required("member")
def member_track_view(request):
    today = timezone.localdate()
    delivery = _pick_today_delivery(request.user, today)
    tracking = get_tracking_context(delivery, request.user) if delivery else None
    lat, lon = _map_coords(delivery) if delivery else (None, None)
    return render(
        request,
        "delivery/member/track.html",
        {
            "active": "dashboard",
            "page_title": "Track delivery",
            "delivery": delivery,
            "tracking": tracking,
            "map_url": static_map_url(lat, lon),
        },
    )
