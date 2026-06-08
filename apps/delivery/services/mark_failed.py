"""Service: transition a Delivery to ``failed`` with reason + notes.

Story 4.10. Pure status-transition logic — no I/O beyond the database
write. The HTTP view (apps/delivery/views/volunteer_today.py) validates
the form first, then hands the cleaned ``reason`` slug and free-text
``notes`` to this service.

Design notes
------------
* ``select_for_update`` holds the row inside the surrounding atomic
  block so a stuck retry from the offline queue can't race a manual
  admin update and produce two LogEntry rows for the same failure.
* Idempotency: a second call on an already-failed row is a no-op
  (returns the locked row, does not save). This keeps the audit log
  clean and stops a phone replay from overwriting the original reason.
* ``failure_reason`` is a single text column shaped as ``slug`` or
  ``slug: notes`` — keep it machine-readable so Epic 06 reporting can
  group by slug while still showing the original note to admins.
* The caregiver-alert side effect is **not** invoked here. Story 4.13
  will register a ``post_save`` signal on ``Delivery`` that fires the
  alert when the status flips to ``failed``; this service only owns
  the status transition.
"""
from __future__ import annotations

from django.db import transaction

from apps.delivery.models import Delivery

#: The four UI reason slugs the volunteer screen shows as radio chips.
#: Anything else is a programmer error — the form already constrains
#: the inbound value, so this set is the second-line guard.
VALID_REASONS = frozenset(
    {"not_home", "no_answer", "refused", "address_wrong"}
)


@transaction.atomic
def mark_failed(
    delivery: Delivery, *, reason: str, notes: str
) -> Delivery:
    """Flip ``delivery`` to ``failed`` and persist ``failure_reason``.

    The text format is ``slug`` when ``notes`` is empty, otherwise
    ``slug: notes``. Returns the refreshed delivery row.

    Raises ``ValueError`` if ``reason`` is not one of
    :data:`VALID_REASONS`. Idempotent on rows already ``failed``.
    """
    if reason not in VALID_REASONS:
        raise ValueError(f"invalid reason: {reason}")

    locked = Delivery.objects.select_for_update().get(pk=delivery.pk)
    if locked.status == "failed":
        return locked

    locked.status = "failed"
    locked.failure_reason = (
        f"{reason}: {notes}" if notes else reason
    )
    locked.save(
        update_fields=["status", "failure_reason", "updated_at"]
    )
    return locked
