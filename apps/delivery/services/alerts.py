"""Notify caregivers when a delivery fails.

Story 4.13. Triggered by the ``post_save`` signal on :class:`Delivery`
(see :mod:`apps.delivery.signals`) once :func:`mark_failed
<apps.delivery.services.mark_failed.mark_failed>` flips ``status`` to
``failed``. The signal enqueues
:func:`apps.delivery.tasks.alerts.send_failure_alert` which calls
:func:`notify_caregivers_of_failure` in a django-q2 worker.

Design notes
------------
* **Caregiver join.** The locked schema names the through table
  ``member_caregivers`` and the related manager (per
  :class:`apps.accounts.models.caregiver_links.CaregiverLink`) is
  ``member.caregiver_links_as_member``. We follow ``mc.caregiver`` to
  fetch the actual caregiver :class:`User` row.
* **Phone column.** The v1 :class:`User` model has no ``phone`` field
  (see :class:`apps.accounts.models.users.User`). We read it via
  ``getattr(caregiver, "phone", "") or ""`` so the SMS path is skipped
  cleanly when the value is absent. Tests inject phones by attaching a
  class-level descriptor — see ``test_caregiver_alert.py``.
* **Rate limit.** Per ``(member_id, scheduled_date)`` we send at most
  one SMS in a rolling 24 h window. ``cache.add`` returns ``False`` on
  collision, which is the gate we need — ``set`` would silently
  overwrite and never block.
* **Office fallback.** If a member has zero linked caregivers the email
  goes to :setting:`OFFICE_ALERT_EMAIL`. The office never gets SMS — we
  pass ``phone=None`` in that branch.
"""
from __future__ import annotations

from django.conf import settings
from django.core.cache import cache
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

from apps.core.services.sms import send_sms
from apps.delivery.models import Delivery

#: 24 hours, in seconds. The rate-limit key is per ``(member, date)`` so
#: the TTL only needs to cover one Melbourne service day.
SMS_TTL = 24 * 60 * 60


def _rate_key(delivery: Delivery) -> str:
    """Cache key gating the per-(member, date) SMS rate limit."""
    return (
        f"sms:{delivery.member_id}:{delivery.scheduled_date.isoformat()}"
    )


def _recipients(delivery: Delivery):
    """Yield ``(email, phone_or_None)`` tuples for the alert.

    * If the member has one or more linked caregivers, returns one tuple
      per caregiver with a usable email. ``phone`` is whatever the
      caregiver row exposes via ``getattr(..., "phone", "")``.
    * If the member has zero linked caregivers, returns a single tuple
      ``(OFFICE_ALERT_EMAIL, None)`` — the office never gets SMS.
    """
    links = list(
        delivery.member.caregiver_links_as_member
        .select_related("caregiver")
    )
    if links:
        out = []
        for mc in links:
            cg = mc.caregiver
            if not cg.email:
                continue
            phone = (getattr(cg, "phone", "") or "").strip() or None
            out.append((cg.email, phone))
        if out:
            return out
    return [(settings.OFFICE_ALERT_EMAIL, None)]


def notify_caregivers_of_failure(delivery: Delivery) -> None:
    """Send the failure email (+ rate-limited SMS) for ``delivery``.

    Renders the email + SMS templates once, then iterates recipients.
    The SMS gate uses ``cache.add`` so two failed deliveries for the
    same member on the same day collapse to a single SMS.
    """
    ctx = {
        "delivery": delivery,
        "member": delivery.member,
        # ``failure_reason`` is stored as ``slug`` or ``slug: notes`` by
        # mark_failed — split on ``:`` so the email shows the bare slug
        # without the volunteer's free-text note.
        "reason": (delivery.failure_reason or "").split(":", 1)[0],
        "office_phone": getattr(settings, "OFFICE_PHONE", "03 9000 0000"),
    }
    html = render_to_string("delivery/emails/delivery_failed.html", ctx)
    txt = render_to_string("delivery/emails/delivery_failed.txt", ctx)
    sms_body = render_to_string(
        "delivery/sms/delivery_failed.txt", ctx
    ).strip()

    sms_allowed = cache.add(_rate_key(delivery), 1, SMS_TTL)

    subject = (
        f"MerryMeal: today's delivery for "
        f"{delivery.member.full_name} failed"
    )

    for email, phone in _recipients(delivery):
        msg = EmailMultiAlternatives(
            subject=subject,
            body=txt,
            to=[email],
        )
        msg.attach_alternative(html, "text/html")
        msg.send()

        if phone and sms_allowed:
            send_sms(to=phone, body=sms_body)
            # Only the first caregiver receives the SMS in a multi-
            # caregiver household; subsequent ones still get the email
            # but the rate-limit gate (one SMS per member per day)
            # already burned the cache slot.
            sms_allowed = False
