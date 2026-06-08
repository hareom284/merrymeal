"""Demo CLI wrapper around `generate_deliveries_for_date`.

Usage:
    python manage.py generate_deliveries [--date YYYY-MM-DD]
"""
import datetime as dt

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.delivery.services import generate_deliveries_for_date


class Command(BaseCommand):
    help = "Generate Delivery rows for a given date (default: today)."

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

        report = generate_deliveries_for_date(date)

        self.stdout.write(self.style.SUCCESS(
            f"date={date} created={len(report.created)} "
            f"skipped={len(report.skipped)}"
        ))
        for member_id, reason in report.skipped:
            self.stdout.write(f"  skipped member={member_id} reason={reason}")
