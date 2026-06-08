"""Story 4.14 — reassign a single ``Delivery`` to a different volunteer.

The admin "today" widget uses this when a volunteer phones in sick. We
keep the rules tight so the manual workflow can't drift from the
nightly packer (Story 4.7):

* Only users with ``role='volunteer'`` may receive a stop.
* Reassigning to the volunteer already on the delivery is rejected
  (silent no-ops mask bugs and the row-swap UI shows nothing changed).
* The target volunteer's route for ``delivery.scheduled_date`` is
  reused if it exists, otherwise a new planned route is created.
* The same 12-stop cap that ``services.dispatch`` enforces is checked
  inside the transaction so two simultaneous reassigns can't overrun
  it.
* An ``auditlog`` ``LogEntry`` is written so admins can audit the
  switch later.
"""
from __future__ import annotations

from auditlog.models import LogEntry
from django.db import transaction
from django.utils import timezone

from apps.delivery.models import Delivery, Route
from apps.delivery.services.dispatch import MAX_STOPS_PER_ROUTE

__all__ = ["MAX_STOPS_PER_ROUTE", "reassign_delivery"]


@transaction.atomic
def reassign_delivery(delivery: Delivery, *, new_volunteer) -> Delivery:
    """Reassign ``delivery`` to ``new_volunteer``.

    Returns the refreshed delivery row. Raises ``ValueError`` for any
    business-rule violation (wrong role, same volunteer, route cap
    exceeded).
    """
    if getattr(new_volunteer, "role", None) != "volunteer":
        raise ValueError("target user is not a volunteer")

    # Lock the delivery row first so two simultaneous reassigns serialise.
    locked = Delivery.objects.select_for_update().get(pk=delivery.pk)

    old_volunteer_id = locked.volunteer_id
    if old_volunteer_id == new_volunteer.pk:
        raise ValueError("delivery is already assigned to this volunteer")

    target_date = locked.scheduled_date or timezone.localdate()
    route, _ = Route.objects.get_or_create(
        volunteer=new_volunteer,
        route_date=target_date,
        defaults={"status": Route.STATUS_PLANNED},
    )

    # Count *inside* the atomic block so the cap holds under contention.
    # Exclude the delivery being moved in case it's already on the
    # target route (defensive — should never happen given the same-
    # volunteer guard above, but cheap to belt-and-brace).
    stops_on_route = (
        Delivery.objects.filter(route=route).exclude(pk=locked.pk).count()
    )
    if stops_on_route >= MAX_STOPS_PER_ROUTE:
        raise ValueError(
            f"route already at cap ({MAX_STOPS_PER_ROUTE} stops)"
        )

    locked.volunteer = new_volunteer
    locked.route = route
    locked.save(update_fields=["volunteer", "route", "updated_at"])

    LogEntry.objects.log_create(
        instance=locked,
        action=LogEntry.Action.UPDATE,
        changes={
            "volunteer_id": [old_volunteer_id, new_volunteer.pk],
            "route_id": [delivery.route_id, route.pk],
        },
        force_log=True,
    )
    return locked
