"""Story 6.5 — board report data collection service."""
from __future__ import annotations

import datetime as dt

import pytest
from django.utils import timezone

from apps.accounts.models import Application
from apps.accounts.tests.factories import UserFactory
from apps.dashboards.services.board_report import (
    BoardReport,
    build_board_report,
)
from apps.delivery.tests.factories import DeliveryFactory, RouteFactory
from apps.donations.tests.factories import DonationFactory

# Reference month chosen to be well clear of any DST edge: June 2026 in
# Australia/Melbourne starts and ends inside AEST (no DST switch).
YEAR = 2026
MONTH = 6


def _make_aware_in_month(day: int, hour: int = 12) -> dt.datetime:
    """Return an aware datetime inside ``YEAR``/``MONTH``."""
    naive = dt.datetime(YEAR, MONTH, day, hour, 0, 0)
    return timezone.make_aware(naive, timezone.get_current_timezone())


@pytest.mark.django_db
class TestEmptyMonth:
    """A month with no data must return zeros — never None / NULL."""

    def test_returns_zero_for_every_metric(self):
        report = build_board_report(year=YEAR, month=MONTH)
        assert isinstance(report, BoardReport)
        assert report.period_label == "June 2026"
        assert report.year == YEAR
        assert report.month == MONTH
        assert report.donations_total_cents == 0
        assert report.donations_count == 0
        assert report.recurring_count == 0
        assert report.deliveries_completed == 0
        assert report.deliveries_failed == 0
        assert report.new_members == 0
        assert report.active_volunteers == 0


@pytest.mark.django_db
class TestDonations:
    """Only ``status="completed"`` counts toward the board number.

    The Donation model uses ``"completed"`` (see
    ``apps/donations/models/donations.py``); the test deliberately
    seeds the other four states to prove they are filtered out.
    """

    def _seed_one(self, status: str, amount: int = 5_000, **extra):
        d = DonationFactory(status=status, amount_cents=amount, **extra)
        # ``DonationFactory`` doesn't expose created_at; force it onto
        # the saved row so the month filter sees it.
        d.created_at = _make_aware_in_month(15)
        d.save(update_fields=["created_at", "updated_at"])
        return d

    def test_completed_donations_count_and_total(self):
        self._seed_one("completed", amount=10_00)
        self._seed_one("completed", amount=25_00)
        report = build_board_report(year=YEAR, month=MONTH)
        assert report.donations_count == 2
        assert report.donations_total_cents == 35_00

    def test_non_completed_statuses_excluded(self):
        self._seed_one("completed", amount=10_00)
        # Each of these should be ignored.
        self._seed_one("pending", amount=99_00)
        self._seed_one("failed", amount=99_00)
        self._seed_one("refunded", amount=99_00)
        self._seed_one("cancelled", amount=99_00)
        report = build_board_report(year=YEAR, month=MONTH)
        assert report.donations_count == 1
        assert report.donations_total_cents == 10_00

    def test_recurring_count_is_subset_of_completed(self):
        self._seed_one("completed", amount=10_00, is_recurring=False)
        self._seed_one("completed", amount=15_00, is_recurring=True)
        self._seed_one("completed", amount=20_00, is_recurring=True)
        # A pending recurring should NOT inflate the count.
        self._seed_one("pending", amount=99_00, is_recurring=True)
        report = build_board_report(year=YEAR, month=MONTH)
        assert report.donations_count == 3
        assert report.recurring_count == 2

    def test_donation_outside_month_excluded(self):
        # In month — counts.
        in_month = DonationFactory(status="completed", amount_cents=10_00)
        in_month.created_at = _make_aware_in_month(1)
        in_month.save(update_fields=["created_at", "updated_at"])
        # Previous month — must not count.
        prev = DonationFactory(status="completed", amount_cents=99_00)
        prev.created_at = timezone.make_aware(
            dt.datetime(YEAR, MONTH - 1, 28, 12, 0, 0),
            timezone.get_current_timezone(),
        )
        prev.save(update_fields=["created_at", "updated_at"])
        # Next month — must not count.
        nxt = DonationFactory(status="completed", amount_cents=99_00)
        nxt.created_at = timezone.make_aware(
            dt.datetime(YEAR, MONTH + 1, 2, 12, 0, 0),
            timezone.get_current_timezone(),
        )
        nxt.save(update_fields=["created_at", "updated_at"])

        report = build_board_report(year=YEAR, month=MONTH)
        assert report.donations_count == 1
        assert report.donations_total_cents == 10_00


@pytest.mark.django_db
class TestDeliveries:
    """Delivery counts filter on ``scheduled_date`` plus ``status``."""

    def test_delivered_and_failed_counts_split_correctly(self):
        DeliveryFactory(
            status="delivered", scheduled_date=dt.date(YEAR, MONTH, 5)
        )
        DeliveryFactory(
            status="delivered", scheduled_date=dt.date(YEAR, MONTH, 10)
        )
        DeliveryFactory(
            status="failed", scheduled_date=dt.date(YEAR, MONTH, 7)
        )
        # Pending in-month doesn't count toward either bucket.
        DeliveryFactory(
            status="pending", scheduled_date=dt.date(YEAR, MONTH, 8)
        )
        # Delivered but outside month — excluded.
        DeliveryFactory(
            status="delivered", scheduled_date=dt.date(YEAR, MONTH - 1, 28)
        )
        report = build_board_report(year=YEAR, month=MONTH)
        assert report.deliveries_completed == 2
        assert report.deliveries_failed == 1


@pytest.mark.django_db
class TestMembership:
    def test_new_members_counts_approvals_in_month(self):
        # Approved within month — counts.
        Application.objects.create(
            full_name="Alice",
            email="alice@example.com",
            dob=dt.date(1950, 1, 1),
            status=Application.STATUS_APPROVED,
            approved_at=_make_aware_in_month(3),
        )
        # Approved last month — excluded.
        Application.objects.create(
            full_name="Bob",
            email="bob@example.com",
            dob=dt.date(1950, 1, 1),
            status=Application.STATUS_APPROVED,
            approved_at=timezone.make_aware(
                dt.datetime(YEAR, MONTH - 1, 20, 9, 0, 0),
                timezone.get_current_timezone(),
            ),
        )
        # Submitted (not yet approved) — excluded.
        Application.objects.create(
            full_name="Carol",
            email="carol@example.com",
            dob=dt.date(1950, 1, 1),
            status=Application.STATUS_SUBMITTED,
        )
        report = build_board_report(year=YEAR, month=MONTH)
        assert report.new_members == 1

    def test_active_volunteers_distinct_count(self):
        # Two routes by the SAME volunteer in-month — one distinct
        # volunteer.
        vol = UserFactory(role="volunteer", email="v1@mm.com")
        RouteFactory(
            volunteer=vol,
            route_date=dt.date(YEAR, MONTH, 4),
            status="completed",
        )
        RouteFactory(
            volunteer=vol,
            route_date=dt.date(YEAR, MONTH, 11),
            status="in_progress",
        )
        # A different volunteer in-month — adds one to the count.
        vol2 = UserFactory(role="volunteer", email="v2@mm.com")
        RouteFactory(
            volunteer=vol2,
            route_date=dt.date(YEAR, MONTH, 6),
            status="planned",
        )
        # Cancelled route shouldn't promote a volunteer to "active".
        vol3 = UserFactory(role="volunteer", email="v3@mm.com")
        RouteFactory(
            volunteer=vol3,
            route_date=dt.date(YEAR, MONTH, 15),
            status="cancelled",
        )
        # Out of month — excluded.
        vol4 = UserFactory(role="volunteer", email="v4@mm.com")
        RouteFactory(
            volunteer=vol4,
            route_date=dt.date(YEAR, MONTH - 1, 28),
            status="completed",
        )
        report = build_board_report(year=YEAR, month=MONTH)
        assert report.active_volunteers == 2


class TestMonthValidation:
    """Pure function — no DB needed."""

    def test_rejects_month_out_of_range(self):
        with pytest.raises(ValueError):
            build_board_report(year=YEAR, month=13)
        with pytest.raises(ValueError):
            build_board_report(year=YEAR, month=0)
