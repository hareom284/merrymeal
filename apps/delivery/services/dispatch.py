"""apps/delivery/services/dispatch.py

Story 4.6 — generate today's `Delivery` rows for every active member.

`generate_deliveries_for_date(date)` is idempotent: re-running for the
same date is a no-op for members that already have a delivery for that
date. The idempotency key is `(member_id, scheduled_date)`.

Trade-offs (v1, charity scale ~ <= 500 members / < 10 kitchens):

* Closest-kitchen distance is computed in Python with the Haversine
  formula (`apps.core.geo.haversine_km`). A Postgres + PostGIS KNN
  index would push this into the DB at a later date — out of scope
  here.
* Primary address: the `user_addresses` table has no `is_primary`
  flag. Until Epic 02 ships that flag, we treat "earliest by
  `created_at`, tiebreak by `id`" as the primary address.
* Placeholder volunteer: `Delivery.volunteer` is `NOT NULL`, but the
  real assignment happens in Story 4.7's route packer. We pin every
  freshly-generated row to a single placeholder user
  (`settings.DISPATCH_PLACEHOLDER_VOLUNTEER_ID`, falling back to the
  first active volunteer).

Schema discrepancy with the story spec
--------------------------------------
The story spec filters with `Kitchen.objects.filter(is_active=True)`,
but `Kitchen` has no `is_active` column in the locked schema. We drop
the filter and use `Kitchen.objects.all()` instead. Re-introduce the
filter only if/when the column is added by a future migration.
"""
from __future__ import annotations

import dataclasses
import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction

from apps.accounts.models import Address
from apps.core.geo import haversine_km
from apps.delivery.models import Delivery, Route
from apps.delivery.services.deliveries import create_delivery
from apps.kitchens.models import Kitchen
from apps.planning.models import MealPlan
from apps.volunteers.models import Availability

logger = logging.getLogger("merrymeal.dispatch")
User = get_user_model()

# Maximum deliveries (stops) we will pack onto a single volunteer's route
# for a given day. Imported by ``apps.delivery.services.reassign`` so the
# manual-reassign widget enforces the same cap as the nightly packer.
MAX_STOPS_PER_ROUTE = 12
ROUTE_CAPACITY = MAX_STOPS_PER_ROUTE
_WEEKDAY_TO_ENUM = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]


@dataclasses.dataclass
class DispatchReport:
    """Result of a single `generate_deliveries_for_date(date)` run."""

    created: list[Delivery]
    skipped: list[tuple[int, str]]  # (member_id, reason)


def _primary_address(member) -> Address | None:
    """Return the member's primary address (earliest by created_at, tiebreak id).

    Skips addresses with missing lat/lng — they cannot drive a
    closest-kitchen lookup.
    """
    return (
        Address.objects
        .filter(user=member, latitude__isnull=False, longitude__isnull=False)
        .order_by("created_at", "id")
        .first()
    )


def _closest_active_kitchen(lat, lon) -> Kitchen | None:
    """Return the closest kitchen to (lat, lon) by Haversine distance.

    NOTE: The story spec calls for an `is_active=True` filter, but the
    `Kitchen` schema has no `is_active` column. We iterate every
    kitchen until that flag exists.
    """
    kitchens = list(Kitchen.objects.all())
    if not kitchens:
        return None
    return min(
        kitchens,
        key=lambda k: haversine_km(
            float(lat), float(lon), float(k.latitude), float(k.longitude)
        ),
    )


def _placeholder_volunteer():
    """Resolve the placeholder volunteer user.

    Resolution order:
      1. `settings.DISPATCH_PLACEHOLDER_VOLUNTEER_ID` if set and the
         user exists.
      2. First active volunteer ordered by id.
      3. `RuntimeError` — caller must seed a volunteer.
    """
    placeholder_id = getattr(settings, "DISPATCH_PLACEHOLDER_VOLUNTEER_ID", None)
    if placeholder_id:
        try:
            return User.objects.get(pk=placeholder_id)
        except User.DoesNotExist:
            logger.warning(
                "DISPATCH_PLACEHOLDER_VOLUNTEER_ID=%s not found; falling back",
                placeholder_id,
            )
    vol = (
        User.objects
        .filter(role="volunteer", is_active=True)
        .order_by("id")
        .first()
    )
    if vol is None:
        raise RuntimeError(
            "No volunteer available for dispatch placeholder. "
            "Seed at least one volunteer or set "
            "DISPATCH_PLACEHOLDER_VOLUNTEER_ID."
        )
    return vol


def generate_deliveries_for_date(date) -> DispatchReport:
    """Create one `Delivery` per active member for `date`. Idempotent.

    Re-running on the same date is a no-op for members that already
    have a delivery for that date (the idempotency key is
    `(member_id, scheduled_date)`).
    """
    placeholder = _placeholder_volunteer()
    created: list[Delivery] = []
    skipped: list[tuple[int, str]] = []

    members = User.objects.filter(
        role="member", is_active=True, deleted_at__isnull=True,
    ).order_by("id")

    for member in members:
        # Idempotency: skip members that already have a delivery for this date.
        if Delivery.objects.filter(member=member, scheduled_date=date).exists():
            logger.info(
                "member=%s skipped: already has delivery for date=%s",
                member.id, date,
            )
            continue

        address = _primary_address(member)
        if address is None:
            logger.warning("member=%s skipped: no address", member.id)
            skipped.append((member.id, "no_address"))
            continue

        kitchen = _closest_active_kitchen(address.latitude, address.longitude)
        if kitchen is None:
            logger.warning("member=%s skipped: no active kitchen", member.id)
            skipped.append((member.id, "no_kitchen"))
            continue

        plan = (
            MealPlan.objects
            .filter(kitchen=kitchen, service_date=date)
            .first()
        )
        if plan is None:
            logger.warning(
                "member=%s skipped: no meal plan for kitchen=%s date=%s",
                member.id, kitchen.id, date,
            )
            skipped.append((member.id, "no_plan"))
            continue

        with transaction.atomic():
            delivery = create_delivery(
                member=member,
                member_address=address,
                meal_plan=plan,
                volunteer=placeholder,
                scheduled_date=date,
            )
        created.append(delivery)

    logger.info(
        "generate_deliveries_for_date date=%s created=%d skipped=%d",
        date, len(created), len(skipped),
    )
    return DispatchReport(created=created, skipped=skipped)


# ---------------------------------------------------------------------------
# Story 4.7 — assign_routes_for_date (greedy route packer)
# ---------------------------------------------------------------------------
#
# v1 algorithm: greedy nearest-from-kitchen pack. Real vehicle-routing
# optimisation (load balancing, two-opt, time windows) lands in Epic 07
# backlog.


@dataclasses.dataclass
class PackReport:
    """Result of a single `assign_routes_for_date(date)` run."""

    routes_created: list[Route]
    unassigned: list[Delivery]


def _pack_chunk_into_route(volunteer, route_date, chunk):
    """Create a planned Route for `volunteer` and attach the chunk's deliveries."""
    route = Route.objects.create(
        volunteer=volunteer,
        route_date=route_date,
        status=Route.STATUS_PLANNED,
    )
    Delivery.objects.filter(pk__in=[d.pk for d in chunk]).update(
        route=route, volunteer=volunteer,
    )
    return route


def _available_volunteers(date) -> list:
    """Volunteers with `morning` availability on the weekday of `date`.

    v1 hard-codes `day_phrase="morning"`. Afternoon/evening routing is
    deferred until we have evening volunteers (Epic 07).
    """
    day_enum = _WEEKDAY_TO_ENUM[date.weekday()]
    vol_ids = (
        Availability.objects
        .filter(day_of_week=day_enum, day_phrase="morning")
        .values_list("volunteer_id", flat=True)
        .distinct()
    )
    return list(
        User.objects.filter(pk__in=vol_ids, is_active=True, role="volunteer")
        .order_by("id")
    )


def _clear_planned_routes_for_date(date) -> None:
    """Wipe `planned` routes for `date`, returning their deliveries to the
    unassigned pool. Leaves `in_progress` / `completed` / `cancelled`
    routes untouched.
    """
    planned = Route.objects.filter(
        route_date=date, status=Route.STATUS_PLANNED,
    )
    Delivery.objects.filter(route__in=planned).update(route=None)
    planned.delete()


def assign_routes_for_date(date) -> PackReport:
    """Greedy-pack today's pending deliveries into `Route`s.

    Algorithm:
      1. Wipe planned routes for `date` (clean-slate idempotency).
      2. For each `(kitchen, date)` pair with unrouted pending deliveries:
         a. Sort deliveries by Haversine distance from the kitchen.
         b. Chunk into groups of `ROUTE_CAPACITY` (12).
         c. Match chunks to volunteers available on `day_of_week+morning`.
         d. Overflow (chunks > volunteers) → log warning, leave unassigned.
    """
    _clear_planned_routes_for_date(date)

    routes_created: list[Route] = []
    unassigned_all: list[Delivery] = []

    pending = (
        Delivery.objects
        .filter(
            scheduled_date=date,
            status=Delivery.STATUS_PENDING,
            route__isnull=True,
        )
        .select_related("meal_plan__kitchen", "member_address")
    )
    by_kitchen: dict[int, list[Delivery]] = {}
    kitchens: dict[int, object] = {}
    for d in pending:
        k = d.meal_plan.kitchen
        by_kitchen.setdefault(k.id, []).append(d)
        kitchens[k.id] = k

    volunteers = _available_volunteers(date)

    for kitchen_id, deliveries in by_kitchen.items():
        kitchen = kitchens[kitchen_id]
        deliveries.sort(key=lambda d: haversine_km(
            float(kitchen.latitude), float(kitchen.longitude),
            float(d.member_address.latitude), float(d.member_address.longitude),
        ))

        # Spread deliveries across available volunteers, capped at
        # ROUTE_CAPACITY per route. With V volunteers and N deliveries,
        # each volunteer carries ceil(N / V) — but never more than 12.
        # Anything beyond V * ROUTE_CAPACITY overflows to unassigned.
        n = len(deliveries)
        v = len(volunteers)
        if v == 0 or n == 0:
            chunk_size = 0
            num_routes = 0
        else:
            chunk_size = min(ROUTE_CAPACITY, -(-n // v))  # ceil division
            num_routes = min(v, -(-n // chunk_size))

        chunks: list[list[Delivery]] = []
        cursor = 0
        for _ in range(num_routes):
            chunk = deliveries[cursor:cursor + chunk_size]
            if not chunk:
                break
            chunks.append(chunk)
            cursor += chunk_size

        with transaction.atomic():
            for chunk, vol in zip(chunks, volunteers[:len(chunks)], strict=True):
                routes_created.append(
                    _pack_chunk_into_route(vol, date, chunk)
                )

        overflow = deliveries[cursor:]
        if overflow:
            logger.warning(
                "overflow: kitchen=%s date=%s unassigned=%d",
                kitchen_id, date, len(overflow),
            )
        unassigned_all.extend(overflow)

    logger.info(
        "assign_routes_for_date date=%s routes=%d unassigned=%d",
        date, len(routes_created), len(unassigned_all),
    )
    return PackReport(routes_created=routes_created, unassigned=unassigned_all)
