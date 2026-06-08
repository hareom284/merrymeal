"""Signal handlers for the delivery app.

Story 4.13. The single handler here listens for ``Delivery`` rows
flipping to ``status='failed'`` and enqueues a django-q2 task that
sends the caregiver alert. We intentionally do **not** call the alert
service inline — the volunteer's HTTP request returns immediately and
the queue absorbs the SMTP / Twilio latency.

Dedupe strategy
---------------
* ``post_save`` fires on every ``.save()``. We guard with:
  1. A status check (``instance.status == 'failed'``) — the only state
     we care about.
  2. An ``update_fields`` check — :func:`mark_failed
     <apps.delivery.services.mark_failed.mark_failed>` writes
     ``["status", "failure_reason", "updated_at"]`` so we know
     ``status`` was actually touched. A POD-photo upload (which writes
     ``["photo", "updated_at"]``) is ignored.
  3. A per-delivery cache gate (``cache.add`` returns ``False`` on
     collision) so a manual admin save that re-touches ``status`` does
     not enqueue a second alert.
"""
from __future__ import annotations

from django.core.cache import cache
from django.db.models.signals import post_save
from django.dispatch import receiver
from django_q.tasks import async_task

from apps.delivery.models import Delivery

#: One-hour TTL on the per-delivery dedupe key. Sized so legitimate
#: retries from the queue (which the queue handles internally) do not
#: leak through, but a same-day repeat fail of the same delivery (e.g.
#: an admin un-fails and re-fails for clerical reasons) still sends a
#: fresh alert.
ALERT_DEDUPE_TTL = 60 * 60


@receiver(post_save, sender=Delivery)
def on_delivery_saved(
    sender,
    instance: Delivery,
    created: bool,
    update_fields,
    **kwargs,
):
    """Enqueue the caregiver alert when a delivery flips to ``failed``."""
    if instance.status != "failed":
        return
    if update_fields is not None and "status" not in update_fields:
        return
    if not cache.add(f"alert-fired:{instance.pk}", 1, ALERT_DEDUPE_TTL):
        return
    async_task(
        "apps.delivery.tasks.alerts.send_failure_alert",
        instance.pk,
    )
