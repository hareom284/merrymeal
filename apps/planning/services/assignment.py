from __future__ import annotations

import datetime as dt
from typing import Literal

from apps.core.geo import haversine_km
from apps.planning.services.exceptions import AddressMissingError

MealType = Literal["fresh", "frozen"]


def _primary_address(member):
    """Return the member's primary address (with lat/lng) or None.

    Falls back to "first by id" if a richer primary_address property is
    not defined on the user model yet.
    """
    addr = getattr(member, "primary_address", None)
    if addr is None:
        rel = getattr(member, "user_addresses", None) or getattr(member, "addresses", None)
        if rel is None:
            return None
        addr = rel.order_by("id").first()
    if addr is None:
        return None
    if addr.latitude is None or addr.longitude is None:
        return None
    return addr


def assign_meal_type(member, kitchen, service_date: dt.date) -> MealType:
    """Return 'fresh' or 'frozen' for a (member, kitchen, service_date).

    Rules — applied in order:
      1. Saturday/Sunday -> 'frozen'.
      2. Weekday + member within kitchen.service_radius_km -> 'fresh'.
      3. Weekday + member outside the radius -> 'frozen'.
      4. Boundary (distance == radius) -> 'fresh'.

    Raises:
      AddressMissingError — if the member has no usable address.
    """
    if service_date.weekday() in (5, 6):
        return "frozen"

    addr = _primary_address(member)
    if addr is None:
        raise AddressMissingError(
            f"member id={getattr(member, 'pk', None)} has no usable address"
        )

    distance_km = haversine_km(
        float(addr.latitude), float(addr.longitude),
        float(kitchen.latitude), float(kitchen.longitude),
    )
    radius_km = float(kitchen.service_radius_km)

    return "fresh" if distance_km <= radius_km else "frozen"
