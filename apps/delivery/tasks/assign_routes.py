"""Django-Q2 callable for the daily route packer.

The Q-cluster picks this up via the `Schedule` row registered in
`DeliveryConfig.ready()`. Cron: 04:30 Australia/Melbourne — 30 minutes
after `generate_deliveries_for_today` so the deliveries it packs are
already in place.
"""
import logging

from django.utils import timezone

from apps.delivery.services import assign_routes_for_date

logger = logging.getLogger("merrymeal.dispatch")


def run_for_today() -> dict:
    """Pack today's pending deliveries into Routes for available volunteers.

    Returns a small dict so the Q-task result page shows useful counts.
    """
    today = timezone.localdate()
    report = assign_routes_for_date(today)
    return {
        "date": today.isoformat(),
        "routes": len(report.routes_created),
        "unassigned": len(report.unassigned),
    }
