import logging
from collections import defaultdict
from datetime import timedelta

from django.core.mail import EmailMultiAlternatives
from django.db import IntegrityError, transaction
from django.template.loader import render_to_string
from django.utils import timezone

from apps.accounts.models import User
from apps.kitchens.models import ExpiryAlertLog, Kitchen
from apps.kitchens.services.expiry import find_expiring_batches


logger = logging.getLogger(__name__)


def _recipient_email() -> str | None:
    """v1: first active user with role='admin'. Returns None if none exists."""
    admin = (
        User.objects
        .filter(role="admin", is_active=True)
        .order_by("id")
        .first()
    )
    return admin.email if admin else None


def _group_by_ingredient(batches):
    grouped: dict[int, list] = defaultdict(list)
    for b in batches:
        grouped[b.ingredient_id].append(b)
    return [(items[0].ingredient, items) for items in grouped.values()]


def _send_for_kitchen(kitchen: Kitchen, *, recipient: str, today) -> bool:
    batches = list(find_expiring_batches(kitchen, within_days=3))
    if not batches:
        return False

    cutoff = today + timedelta(days=3)
    context = {
        "kitchen": kitchen,
        "today": today,
        "cutoff": cutoff,
        "ingredient_groups": _group_by_ingredient(batches),
    }

    try:
        with transaction.atomic():
            ExpiryAlertLog.objects.create(kitchen=kitchen, sent_date=today)

            subject = f"Expiring batches at {kitchen.name}"
            txt_body = render_to_string("kitchens/emails/expiring_batches.txt", context)
            html_body = render_to_string("kitchens/emails/expiring_batches.html", context)

            msg = EmailMultiAlternatives(subject, txt_body, to=[recipient])
            msg.attach_alternative(html_body, "text/html")
            msg.send(fail_silently=False)
    except IntegrityError:
        logger.info("expiry alert already sent today for kitchen=%s", kitchen.id)
        return False

    return True


def send_expiry_alerts():
    """Django-Q2 entry point. Runs daily at 06:00 Melbourne via the Schedule
    row created in migration 0006_schedule_expiry_alerts."""
    today = timezone.localdate()
    recipient = _recipient_email()

    for kitchen in Kitchen.objects.all().order_by("id"):
        if recipient is None:
            logger.warning("no admin recipient configured; skipping kitchen=%s", kitchen.id)
            continue
        _send_for_kitchen(kitchen, recipient=recipient, today=today)
