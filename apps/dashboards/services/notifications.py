"""Synthesised notifications for the member notifications page (Story 12.6).

There is no ``Notification`` row in the schema — every item rendered on
``/notifications/`` is derived at request time from data the member
dashboard already reads: today's Delivery row, the last delivered meal
without DeliveryFeedback, and the meal plan for the day after today.

Returning plain dicts (not model instances) keeps the template dumb and
the test surface small: any new notification type is a new branch here,
no migration required.

Public entrypoint:
    build_member_notifications(user, today=None) -> list[dict]
"""
from __future__ import annotations

import datetime as dt
from typing import Any

from django.urls import reverse
from django.utils import timezone

from apps.dashboards.services.member_today import _nearest_kitchen_for
from apps.delivery.models import Delivery
from apps.planning.models import MealPlan


def _today_delivery_item(member, today: dt.date) -> dict[str, Any] | None:
    delivery = (
        Delivery.objects
        .filter(member=member, scheduled_date=today)
        .select_related("volunteer", "meal_plan__meal")
        .order_by("-id")
        .first()
    )
    if delivery is None:
        return None

    status = delivery.status
    if status == Delivery.STATUS_DELIVERED:
        title = "Your meal was delivered"
        body = "Hope you enjoyed it. Tap to rate your meal."
    elif status == Delivery.STATUS_OUT_FOR_DELIVERY:
        volunteer = (
            delivery.volunteer.full_name.split()[0]
            if delivery.volunteer and delivery.volunteer.full_name
            else "Your volunteer"
        )
        title = "Your meal is on the way"
        body = f"{volunteer} is bringing it now."
    elif status == Delivery.STATUS_FAILED:
        title = "We couldn't deliver today"
        body = (
            delivery.failure_reason
            or "We'll be in touch shortly."
        )
    else:
        title = "Today's meal is scheduled"
        body = "We'll let you know when it leaves the kitchen."

    return {
        "kind": "delivery",
        "title": title,
        "body": body,
        "when": "Today",
        "icon": "truck",
        "url": reverse("delivery:tracking_status", args=[delivery.id]),
    }


def _feedback_pending_item(member, today: dt.date) -> dict[str, Any] | None:
    """Most recent delivered meal in the last 2 days that the member
    has not rated yet. Mirrors the dashboard's feedback prompt so the
    notification list and the dashboard CTA can never disagree."""
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
    yesterday = today - dt.timedelta(days=1)
    return {
        "kind": "feedback",
        "title": f"How was {meal_name}?",
        "body": "Two taps to tell us how it tasted.",
        "when": "Yesterday" if delivery.scheduled_date == yesterday else delivery.scheduled_date.strftime("%a %d %b"),
        "icon": "star",
        "url": reverse("delivery:tracking_status", args=[delivery.id]),
    }


def _tomorrows_meal_item(member, today: dt.date) -> dict[str, Any] | None:
    """Surface the meal the member is scheduled for tomorrow, if any."""
    tomorrow = today + dt.timedelta(days=1)
    candidates = list(
        MealPlan.objects
        .filter(service_date=tomorrow)
        .select_related("kitchen", "meal")
    )
    if not candidates:
        return None
    plan = _nearest_kitchen_for(member, candidates)
    if plan is None:
        return None
    return {
        "kind": "menu",
        "title": f"Tomorrow's meal: {plan.meal.name}",
        "body": "From your assigned kitchen.",
        "when": "Tomorrow",
        "icon": "menu",
        "url": reverse("dashboards:weekly_menu"),
    }


def build_member_notifications(user, today: dt.date | None = None) -> list[dict[str, Any]]:
    """Return the ordered list of notification dicts for ``user``.

    Order: most-actionable first (failed/out-for-delivery → feedback
    pending → upcoming menu). Items are dicts so the template treats
    each row identically; the ``kind`` field drives the icon and the
    visual badge.
    """
    today = today or timezone.localdate()
    items: list[dict[str, Any]] = []
    for builder in (_today_delivery_item, _feedback_pending_item, _tomorrows_meal_item):
        item = builder(user, today)
        if item is not None:
            items.append(item)
    return items
