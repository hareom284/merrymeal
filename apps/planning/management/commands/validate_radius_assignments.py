"""Walk active members and assert today's fresh/frozen assignment matches
the rule in apps.planning.services.assignment.assign_meal_type.

Used in two places:

* A nightly Django-Q2 task that emails ADMIN_EMAIL on non-zero exit
  (see apps.planning.tasks.validate.run_nightly_validation).
* A non-blocking CI job — the result is visible in PR logs but doesn't
  gate merge yet.

The "actual" assignment for v1 comes from the most recent ``MealPlan``
row for the (kitchen, service_date) pair: it tells us the kitchen-wide
type. Per-member outside-radius routing is applied at delivery
generation (Epic 04); once that lands a follow-up story extends this
command to walk ``Delivery`` rows.
"""

from __future__ import annotations

import datetime as dt
import sys

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.accounts.models import User
from apps.kitchens.models import Kitchen
from apps.planning.models import MealPlan
from apps.planning.services.assignment import (
    _primary_address,
    assign_meal_type,
)
from apps.planning.services.exceptions import AddressMissingError


class Command(BaseCommand):
    help = "Verify every active member's fresh/frozen assignment for today."

    def add_arguments(self, parser):
        parser.add_argument(
            "--date",
            help="ISO date (YYYY-MM-DD). Defaults to today in Australia/Melbourne.",
        )
        parser.add_argument(
            "--quiet",
            action="store_true",
            help="Suppress per-member inconsistency lines; print summary only.",
        )

    def handle(self, *args, **options):
        target = (
            dt.date.fromisoformat(options["date"])
            if options.get("date")
            else timezone.localdate()
        )
        quiet = options["quiet"]

        plans_by_kitchen_date = {
            (p.kitchen_id, p.service_date): p
            for p in MealPlan.objects.filter(service_date=target)
        }

        members = User.objects.filter(role="member", is_active=True)
        kitchens = list(Kitchen.objects.all())

        ok = bad = skipped = 0
        for member in members:
            # Detect a missing address once per member — independent of how
            # many kitchens exist, so a member with no address still shows
            # up in the "skipped" tally even on a fresh DB.
            if _primary_address(member) is None:
                skipped += 1
                continue
            for kitchen in kitchens:
                try:
                    expected = assign_meal_type(member, kitchen, target)
                except AddressMissingError:
                    # Should not happen — _primary_address already screened
                    # — but guard defensively so a flaky lat/lng row can't
                    # crash the nightly task.
                    break
                plan = plans_by_kitchen_date.get((kitchen.id, target))
                if plan is None:
                    # No plan for this (kitchen, date) — nothing to validate.
                    continue
                actual = plan.meal_type
                if expected != actual:
                    bad += 1
                    if not quiet:
                        self.stdout.write(
                            f"member {member.id} {member.email}  "
                            f"kitchen {kitchen.id}  "
                            f"expected={expected}  actual={actual}"
                        )
                else:
                    ok += 1

        if skipped and not quiet:
            self.stdout.write(
                f"skipped: {skipped} member(s) without addresses"
            )

        if bad:
            # Count members affected: distinct error lines already; rough
            # estimate uses bad as both inconsistencies and members for
            # the summary string the DoD requires.
            self.stdout.write(
                self.style.ERROR(
                    f"FAIL: {bad} inconsistency(ies); {ok} consistent"
                )
            )
            sys.exit(1)
        self.stdout.write(self.style.SUCCESS(f"OK: {ok} consistent"))
        sys.exit(0)
