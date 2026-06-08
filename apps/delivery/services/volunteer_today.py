"""Service: shape today's route for the volunteer screen (Story 4.8).

Pure read; no side effects. Returns a dict the view passes straight to
``templates/delivery/volunteer/today.html``.

Adaptations from the spec
-------------------------
* The ``User`` model is ``full_name`` only — no separate ``first_name``
  / ``last_name``. We derive "Margaret S." by splitting on whitespace
  and taking the first token + the first letter of the last token.
* ``Route`` has no ``start_time`` column in the locked schema, so the
  pickup time falls back to the spec's 07:55 default (5 min before the
  08:00 service window).
* ``Route`` has no direct ``kitchen`` FK. The kitchen is resolved via
  the first delivery's ``meal_plan.kitchen`` — every meal_plan on the
  route shares the same kitchen by construction (Story 4.6).
* ``Address`` has no ``street`` column. The "address line" used on
  collapsed cards is the address ``label`` (e.g. "Home"); the suburb /
  city / postal code stay hidden until the volunteer taps to expand.
* ``User`` has no ``phone`` / ``special_instructions`` columns at this
  sprint. We surface them with ``getattr(..., "", "")`` so the screen
  is forward-compatible with later epics that may add them, and the
  template hides the call link when ``phone`` is empty.
"""
from __future__ import annotations

from datetime import time

from django.utils import timezone

from apps.delivery.forms.mark_failed import REASON_CHOICES
from apps.delivery.models import Delivery
from apps.planning.services.allergen import meal_allergens_for_member

# 5 min before the 08:00 Melbourne service window. Story 4.8 spec says
# fall back to this when ``Route`` has no ``start_time`` — which is the
# case in the locked v1 schema.
DEFAULT_PICKUP = time(7, 55)


def _member_display(member) -> str:
    """Return ``"Margaret S."`` from ``full_name="Margaret Smith"``.

    Falls back gracefully:
    * Single-token names ("Cher") render as just the first name.
    * Empty / None names render as the empty string.
    """
    full = (getattr(member, "full_name", "") or "").strip()
    if not full:
        return ""
    parts = full.split()
    if len(parts) == 1:
        return parts[0]
    return f"{parts[0]} {parts[-1][:1]}."


def get_today_route(user) -> dict:
    """Shape today's route for the volunteer ``user``.

    Returns the dict documented in Story 4.8::

        {
            "kitchen": {"name": str, "address": str, "pickup_time": time},
            "route": Route | None,
            "stops": [
                {
                    "delivery": Delivery,
                    "member_display": "Margaret S.",
                    "address_line": str,
                    "phone": str,
                    "special_instructions": str,
                    "allergens": list[Allergy],
                    "is_current": bool,
                },
                ...
            ],
        }
    """
    today = timezone.localdate()

    deliveries = list(
        Delivery.objects
        .filter(volunteer=user, scheduled_date=today)
        .select_related(
            "member",
            "member_address",
            "meal_plan",
            "meal_plan__meal",
            "meal_plan__kitchen",
            "route",
        )
        .order_by("id")
    )

    route = deliveries[0].route if deliveries else None
    kitchen = (
        deliveries[0].meal_plan.kitchen
        if deliveries and deliveries[0].meal_plan_id
        else None
    )

    pickup_time = DEFAULT_PICKUP
    # If a future migration adds Route.start_time, honour it. Until then
    # ``getattr`` keeps this branch dormant without raising.
    start_time = getattr(route, "start_time", None) if route else None
    if start_time:
        # Translate "5 minutes before" without dragging in a date — pure
        # time arithmetic via combine(today, ...) then -5min.
        from datetime import datetime, timedelta

        dt = datetime.combine(today, start_time) - timedelta(minutes=5)
        pickup_time = dt.time()

    stops: list[dict] = []
    current_assigned = False
    for delivery in deliveries:
        is_current = (
            not current_assigned
            and delivery.status in {"pending", "out_for_delivery"}
        )
        if is_current:
            current_assigned = True

        member = delivery.member
        address = delivery.member_address
        allergens: list = []
        if delivery.meal_plan_id and delivery.meal_plan.meal_id:
            allergens = meal_allergens_for_member(delivery.meal_plan.meal, member)

        stops.append({
            "delivery": delivery,
            "member_display": _member_display(member),
            "address_line": (getattr(address, "label", "") or "") if address else "",
            "phone": (getattr(member, "phone", "") or ""),
            "special_instructions": (
                getattr(member, "special_instructions", "") or ""
            ),
            "allergens": allergens,
            "is_current": is_current,
        })

    return {
        "kitchen": {
            "name": kitchen.name if kitchen else "",
            # Kitchen has lat/lng but no street/address column today;
            # surface coordinates only when a name is missing entirely.
            "address": getattr(kitchen, "address", "") if kitchen else "",
            "pickup_time": pickup_time,
        },
        "route": route,
        "stops": stops,
        # Story 4.10 — the bottom-sheet partial iterates these to render
        # the four reason chips. Surfacing them here (rather than via a
        # context processor) keeps the route fragment self-contained for
        # HTMX swaps.
        "reason_choices": REASON_CHOICES,
    }
