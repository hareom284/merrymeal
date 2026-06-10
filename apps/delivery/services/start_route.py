"""Service: flip the volunteer's route to ``in_progress`` + announce
"on the way" to the route's members.

Pairs with the "I'm on my way" CTA at the top of
``templates/delivery/volunteer/_route_fragment.html``. Once the volunteer
taps it after leaving the kitchen, every pending stop on their route
transitions to ``out_for_delivery``, which is what unlocks the live
"On the way" tracking copy and (eventually) the static map block on the
member-facing ``delivery/member/track.html`` page.

Design notes
------------
* Atomic + locked. ``select_for_update`` on the route prevents two
  near-simultaneous taps (e.g. a flaky network retry) from racing the
  bulk delivery update.
* Idempotent. A second call on an already-``in_progress`` route is a
  no-op — no resaved status row, no rewound timestamps, no audit-log
  spam.
* Scoped to one volunteer + one date. Only ``Route.deliveries`` are
  touched, and only the ones still in ``pending``. ``delivered`` and
  ``failed`` rows are explicitly left alone so a re-tap mid-route can
  never rewind closed stops.
"""
from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from apps.delivery.models import Delivery, Route


def start_route(volunteer) -> Route | None:
    """Transition ``volunteer``'s route for today to ``in_progress``.

    Returns the (refreshed) ``Route`` on success, or ``None`` when the
    volunteer has no route scheduled today — the view turns that into
    the "All done" empty-state render rather than a 404, because the
    button is only ever rendered when a planned route exists.
    """
    today = timezone.localdate()

    with transaction.atomic():
        route = (
            Route.objects
            .select_for_update()
            .filter(volunteer=volunteer, route_date=today)
            .first()
        )
        if route is None:
            return None
        if route.status == Route.STATUS_PLANNED:
            route.status = Route.STATUS_IN_PROGRESS
            # ``auto_now=True`` on ``updated_at`` only fires when the
            # field is in ``update_fields`` — same gotcha called out in
            # CLAUDE.md.
            route.save(update_fields=["status", "updated_at"])

        # Always bulk-promote pending → out_for_delivery, even on a
        # second call: the first call may have failed half-way (e.g.
        # the route saved but the bulk update did not), and the second
        # call should heal that. ``update()`` on a filtered queryset is
        # a single SQL ``UPDATE`` — no per-row signals, no per-row
        # ``save()`` overhead.
        Delivery.objects.filter(
            route=route,
            status=Delivery.STATUS_PENDING,
        ).update(
            status=Delivery.STATUS_OUT_FOR_DELIVERY,
            updated_at=timezone.now(),
        )

    route.refresh_from_db()
    return route
