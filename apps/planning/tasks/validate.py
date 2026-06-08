"""Nightly Django-Q2 task wrapping ``validate_radius_assignments``.

Scheduled via the data migration
``apps.planning.migrations.0002_schedule_validate_radius`` so the
``django_q.Schedule`` row lives in the DB the same way the existing
expiry-alerts schedule does (see
``apps.kitchens.migrations.0006_schedule_expiry_alerts``).
"""

from __future__ import annotations

import io
import logging

from django.conf import settings
from django.core import mail
from django.core.management import call_command

log = logging.getLogger(__name__)


def run_nightly_validation() -> int:
    """Run ``validate_radius_assignments``; email admin on failure.

    Returns the command's exit code so Q2 can record it.
    """
    out = io.StringIO()
    code = 0
    try:
        call_command("validate_radius_assignments", stdout=out)
    except SystemExit as exc:
        code = int(exc.code or 0)

    if code != 0:
        body = out.getvalue() or (
            "validate_radius_assignments exited non-zero with no captured "
            "output. Check the Django-Q task log for details."
        )
        # Send to / from the same operator inbox — for a solo-admin setup
        # the two are the same address, so we read DEFAULT_FROM_EMAIL.
        operator_email = getattr(settings, "DEFAULT_FROM_EMAIL", "") or ""
        if operator_email and "@" in operator_email:
            try:
                mail.send_mail(
                    subject="[MerryMeal] validate_radius_assignments FAILED",
                    message=body,
                    from_email=operator_email,
                    recipient_list=[operator_email],
                    fail_silently=True,
                )
            except Exception:
                # SMTP misconfig must not crash the nightly task — log and
                # continue so the next run still gets a chance.
                log.exception(
                    "Failed to email admin about validation failure"
                )
        else:
            log.warning(
                "validate_radius_assignments failed but DEFAULT_FROM_EMAIL "
                "is unset; skipping notification email."
            )
    return code
