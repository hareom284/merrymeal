"""Member dashboard composition service.

The member dashboard renders five distinct sections:

1. Hero (greeting + ETA copy)
2. "Today's delivery" — three-stage progress + assigned volunteer
3. "Today's meal" — meal name, ingredients, allergens
4. "This week's menu" — five-day strip
5. "Rate yesterday's meal" — pending-feedback CTA

For Story 3.4 the meal card was wired to ``MealPlan`` via
``get_today_card``. The other four sections used to be hardcoded mocks
inside the view. This module pulls them from the live ``Delivery`` and
``MealPlan`` tables and returns honest empty states when no data
exists, so the dashboard never lies about who's delivering or what's
on the menu — it either tells the truth or stays quiet.

Public entrypoint:
    build_member_dashboard_context(member, today=None) -> dict
"""
from __future__ import annotations

import datetime as dt
from typing import Any

from django.utils import timezone

from apps.dashboards.services.member_today import get_today_card
from apps.delivery.forms.feedback import TAG_CHOICES
from apps.delivery.models import Delivery
from apps.delivery.services.tracking import get_tracking_context
from apps.planning.models import MealPlan

WEEK_DAY_LABELS = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]


def _initials(full_name: str | None) -> str:
    if not full_name:
        return "?"
    parts = [p for p in full_name.strip().split() if p]
    if not parts:
        return "?"
    if len(parts) == 1:
        return parts[0][:2].upper()
    return (parts[0][0] + parts[-1][0]).upper()


def _format_eta(delivered_time: dt.datetime | None) -> tuple[str, str]:
    """Split a localised datetime into ('12:32', 'PM') for the hero clock.

    Returns ('--:--', '') when there's no time to display.
    """
    if delivered_time is None:
        return ("--:--", "")
    local = timezone.localtime(delivered_time)
    return (local.strftime("%I:%M").lstrip("0") or "12:00", local.strftime("%p"))


def _get_active_delivery(member, today: dt.date) -> Delivery | None:
    """The member's most relevant delivery for today.

    Picks ``out_for_delivery`` first (active right now), then any
    ``pending`` scheduled for today, then today's ``delivered`` or
    ``failed`` row. Returns None when nothing scheduled.
    """
    qs = (
        Delivery.objects
        .filter(member=member, scheduled_date=today)
        .select_related("volunteer", "meal_plan__meal", "route")
    )
    # Priority: active > pending > terminal (delivered/failed).
    by_priority = {
        Delivery.STATUS_OUT_FOR_DELIVERY: 0,
        Delivery.STATUS_PENDING: 1,
        Delivery.STATUS_DELIVERED: 2,
        Delivery.STATUS_FAILED: 3,
    }
    rows = sorted(qs, key=lambda d: by_priority.get(d.status, 9))
    return rows[0] if rows else None


def _build_hero(member, delivery: Delivery | None) -> dict[str, Any]:
    full_name = (member.full_name or member.email or "there").strip()
    greeting_name = full_name.split()[0] if full_name else "there"

    if delivery is None:
        return {
            "greeting_name": greeting_name,
            "eta_text": "No delivery scheduled for today.",
            "eta_time": "--:--",
            "eta_period": "",
        }

    if delivery.status == Delivery.STATUS_DELIVERED:
        eta_time, eta_period = _format_eta(delivery.delivered_time)
        return {
            "greeting_name": greeting_name,
            "eta_text": "Your meal was delivered. Hope you enjoyed it.",
            "eta_time": eta_time,
            "eta_period": eta_period,
        }

    if delivery.status == Delivery.STATUS_FAILED:
        return {
            "greeting_name": greeting_name,
            "eta_text": "We couldn't complete today's delivery. We'll be in touch.",
            "eta_time": "--:--",
            "eta_period": "",
        }

    if delivery.status == Delivery.STATUS_OUT_FOR_DELIVERY:
        return {
            "greeting_name": greeting_name,
            "eta_text": "Your warm meal is on the way.",
            "eta_time": "Soon",
            "eta_period": "",
        }

    # pending
    return {
        "greeting_name": greeting_name,
        "eta_text": "Your meal is scheduled for delivery today.",
        "eta_time": "Today",
        "eta_period": "",
    }


def _build_delivery_card(delivery: Delivery | None) -> dict[str, Any] | None:
    """Returns the 3-stage delivery progress + volunteer block, or None
    if there is no delivery to render."""
    if delivery is None:
        return None

    status_label_by_status = {
        Delivery.STATUS_PENDING: "Scheduled",
        Delivery.STATUS_OUT_FOR_DELIVERY: "On the way",
        Delivery.STATUS_DELIVERED: "Delivered",
        Delivery.STATUS_FAILED: "Delivery failed",
    }

    # Stage state machine (cooked → on the way → delivered).
    if delivery.status == Delivery.STATUS_DELIVERED:
        cooked, on_way, delivered = "done", "done", "done"
    elif delivery.status == Delivery.STATUS_OUT_FOR_DELIVERY:
        cooked, on_way, delivered = "done", "active", "pending"
    elif delivery.status == Delivery.STATUS_FAILED:
        cooked, on_way, delivered = "done", "done", "pending"
    else:  # pending
        cooked, on_way, delivered = "active", "pending", "pending"

    on_way_subtitle = (
        delivery.volunteer.full_name.split()[0]
        if delivery.status == Delivery.STATUS_OUT_FOR_DELIVERY
        and delivery.volunteer
        and delivery.volunteer.full_name
        else "Awaiting volunteer"
    )

    delivered_subtitle = "Today"
    if delivery.delivered_time:
        delivered_subtitle = timezone.localtime(delivery.delivered_time).strftime("%I:%M %p").lstrip("0")

    stages = [
        {"name": "Cooked", "subtitle": "By the kitchen", "state": cooked},
        {"name": "On the way", "subtitle": on_way_subtitle, "state": on_way},
        {"name": "Delivered", "subtitle": delivered_subtitle, "state": delivered},
    ]

    volunteer = None
    if delivery.volunteer:
        volunteer = {
            "initials": _initials(delivery.volunteer.full_name),
            "name": delivery.volunteer.full_name or delivery.volunteer.email,
            "subtitle": "Your volunteer",
        }

    return {
        "status_label": status_label_by_status.get(delivery.status, delivery.status),
        "stages": stages,
        "volunteer": volunteer,
    }


def _get_week_menu(member, today: dt.date) -> list[dict[str, Any]]:
    """Five rolling weekdays starting from this Monday.

    For each day in MON–FRI of the current ISO week, find the MealPlan
    served by the kitchen closest to the member's primary address. If no
    plan exists, the cell shows the day label with a dim placeholder.
    """
    from apps.dashboards.services.member_today import _nearest_kitchen_for

    monday = today - dt.timedelta(days=today.weekday())
    week_dates = [monday + dt.timedelta(days=i) for i in range(5)]

    plans_qs = (
        MealPlan.objects
        .filter(service_date__in=week_dates)
        .select_related("kitchen", "meal")
    )

    # Group plans by date so we can pick the nearest-kitchen plan per day.
    plans_by_date: dict[dt.date, list[MealPlan]] = {}
    for plan in plans_qs:
        plans_by_date.setdefault(plan.service_date, []).append(plan)

    week: list[dict[str, Any]] = []
    for d in week_dates:
        candidates = plans_by_date.get(d, [])
        chosen = _nearest_kitchen_for(member, candidates) if candidates else None
        if chosen is None:
            meal_label = "—"
        else:
            meal_label = chosen.meal.name
        if d < today:
            state = "done"
        elif d == today:
            state = "today"
        else:
            state = "upcoming"
        week.append({
            "day": WEEK_DAY_LABELS[d.weekday()],
            "meal": meal_label,
            "state": state,
        })
    return week


def _get_feedback_prompt(member, today: dt.date) -> dict[str, Any] | None:
    """Most recent delivered meal in the last 2 days that the member has
    not yet rated. Returns None when there's nothing to ask about."""
    cutoff = today - dt.timedelta(days=2)
    delivery = (
        Delivery.objects
        .filter(
            member=member,
            status=Delivery.STATUS_DELIVERED,
            scheduled_date__gte=cutoff,
            scheduled_date__lt=today,
            feedback__isnull=True,
        )
        .select_related("meal_plan__meal")
        .order_by("-scheduled_date")
        .first()
    )
    if delivery is None:
        return None
    meal_name = delivery.meal_plan.meal.name
    # ``delivery`` is the actual Delivery instance; the template hands
    # it to ``templates/delivery/member/_feedback_card.html`` which
    # builds the HTMX form against ``delivery.id``.
    return {
        "delivery": delivery,
        "meal": meal_name,
        "question": f"{meal_name} — how was it?",
        "delivery_id": delivery.id,
    }


def build_member_dashboard_context(member, today: dt.date | None = None) -> dict[str, Any]:
    """One-stop assembly for the member dashboard.

    Returns a dict ready to drop into ``render(request, ..., context)``.
    Every section is sourced from real DB rows; sections with no data
    are returned as ``None`` (or an honest placeholder list for the week
    strip) so the template can hide them rather than fabricate.

    Two keys carry the live ``Delivery`` instance for the orphaned
    today-card partial (Stories 4.11 / 4.12 tracking pill + 2-tap
    feedback): ``today_delivery`` (the instance) and ``tracking`` (the
    dict returned by ``get_tracking_context``). The dashboard-shaped
    ``delivery`` dict above is consumed by the 3-stage progress UI in
    the left column; keeping the two views separate avoids cramming
    presentation flags onto the model instance.
    """
    today = today or timezone.localdate()
    active_delivery = _get_active_delivery(member, today)
    tracking = (
        get_tracking_context(active_delivery, member)
        if active_delivery is not None
        else None
    )
    return {
        "today_date_label": today.strftime("%A, %d %B"),
        "card": get_today_card(member, today=today),
        "hero": _build_hero(member, active_delivery),
        "delivery": _build_delivery_card(active_delivery),
        "week_menu": _get_week_menu(member, today),
        "feedback_prompt": _get_feedback_prompt(member, today),
        "today_delivery": active_delivery,
        "tracking": tracking,
        "tag_choices": TAG_CHOICES,
    }
