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
from apps.delivery.models import Delivery
from apps.delivery.services.deliveries import create_delivery
from apps.kitchens.models import Kitchen
from apps.planning.models import MealPlan

logger = logging.getLogger("merrymeal.dispatch")
User = get_user_model()


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
