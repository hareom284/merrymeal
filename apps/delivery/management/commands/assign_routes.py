"""Demo CLI wrapper around `assign_routes_for_date`.

Usage:
    python manage.py assign_routes [--date YYYY-MM-DD]
"""
import datetime as dt

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.delivery.services import assign_routes_for_date


class Command(BaseCommand):
    help = "Pack today's pending Deliveries into Routes for available volunteers."

    def add_arguments(self, parser):
        parser.add_argument(
            "--date",
            help="ISO date (YYYY-MM-DD). Defaults to today (Australia/Melbourne).",
        )

    def handle(self, *args, **opts):
        if opts["date"]:
            date = dt.date.fromisoformat(opts["date"])
        else:
            date = timezone.localdate()

        report = assign_routes_for_date(date)

        self.stdout.write(self.style.SUCCESS(
            f"date={date} routes={len(report.routes_created)} "
            f"unassigned={len(report.unassigned)}"
        ))
