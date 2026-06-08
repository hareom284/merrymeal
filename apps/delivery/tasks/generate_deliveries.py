"""Django-Q2 callable for the nightly dispatch.

The Q-cluster picks this up via the `Schedule` row registered in
`DeliveryConfig.ready()`. Cron: 04:00 Australia/Melbourne.
"""
import logging

from django.utils import timezone

from apps.delivery.services import generate_deliveries_for_date

logger = logging.getLogger("merrymeal.dispatch")


def run_for_today() -> dict:
    """Generate deliveries for today's date in local time.

    Returns a small dict so the Q-task result page shows useful counts.
    """
    today = timezone.localdate()
    report = generate_deliveries_for_date(today)
    return {
        "date": today.isoformat(),
        "created": len(report.created),
        "skipped": len(report.skipped),
    }
