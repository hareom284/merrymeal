"""django-q2 worker that sends the caregiver failure alert.

Story 4.13. Kept tiny on purpose: the signal hands us a primary key, we
refetch the delivery (the worker may run in another process, so the
in-memory instance from the signal isn't reusable) and delegate to
:func:`apps.delivery.services.alerts.notify_caregivers_of_failure`.
"""
from __future__ import annotations

from apps.delivery.models import Delivery
from apps.delivery.services.alerts import notify_caregivers_of_failure


def send_failure_alert(delivery_id: int) -> None:
    """Resolve the delivery and dispatch the alert.

    Letting any exception propagate is intentional — django-q2 retries
    failed tasks based on the cluster config, so swallowing here would
    hide transient SMTP / Twilio outages from ops.
    """
    delivery = (
        Delivery.objects.select_related("member")
        .get(pk=delivery_id)
    )
    notify_caregivers_of_failure(delivery)
