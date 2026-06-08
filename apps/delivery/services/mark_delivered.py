"""Service: transition a Delivery to ``delivered`` with POD photo + geo.

Story 4.9. Pure status-transition logic — no I/O beyond the database
write. The HTTP view (apps/delivery/views/volunteer_today.py) is
responsible for converting + uploading the photo first, then hands the
resulting URL to this service.

Design notes
------------
* ``select_for_update`` holds the row inside the surrounding atomic
  block so a stuck retry from the offline queue can't race a manual
  admin update and create two LogEntry rows for the same drop-off.
* Idempotency: a second call on an already-delivered row is a no-op
  (returns the locked row, does not save). This keeps the audit log
  clean even if the volunteer's phone replays the same POST.
* ``photo`` is stored as the public URL (e.g. ``S3`` CDN in prod,
  ``/media/pod/…`` in dev), never as a file path. The conversion +
  upload happens in ``services.photo.upload_pod_photo``.
"""
from __future__ import annotations

from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from apps.delivery.models import Delivery


def _coerce_decimal(value):
    """Accept str / float / Decimal / None from form ``cleaned_data``."""
    if value in (None, ""):
        return None
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


@transaction.atomic
def mark_delivered(
    delivery: Delivery,
    *,
    photo_url: str,
    lat=None,
    lng=None,
) -> Delivery:
    """Flip ``delivery`` to ``delivered`` and persist the POD photo + geo.

    Idempotent: if the row is already ``delivered`` the original
    timestamp, photo, and geo are preserved (no save, no audit-log
    spam).
    """
    locked = (
        Delivery.objects.select_for_update().get(pk=delivery.pk)
    )
    if locked.status == "delivered":
        return locked

    locked.status = "delivered"
    locked.delivered_time = timezone.now()
    locked.photo = photo_url
    locked.latitude = _coerce_decimal(lat)
    locked.longitude = _coerce_decimal(lng)
    locked.save(
        update_fields=[
            "status",
            "delivered_time",
            "photo",
            "latitude",
            "longitude",
            "updated_at",
        ]
    )
    return locked
