"""Tests for Story 6.3 — donor history service.

The service is the single data source for the donor history page. It
returns every donation whose ``donor_email`` matches the logged-in
user's email (case-insensitive — Sprint 09 stores whatever address the
donor typed on the donate form, so ``Margaret@Example.com`` must match
the user record ``margaret@example.com``).

Status filtering note
---------------------
The spec calls for hiding ``pending`` / ``failed`` donations and only
showing ``completed`` + ``refunded``. We deliberately diverge — the
donor history view shows every status so the donor can see what
happened to a failed Stripe charge without phoning the office. The
status badge in the template communicates the state.
"""
from __future__ import annotations

import pytest

from apps.accounts.tests.factories import UserFactory
from apps.dashboards.services.donor_history import donor_history
from apps.donations.tests.factories import CampaignFactory, DonationFactory


@pytest.mark.django_db
class TestDonorHistoryService:
    def test_returns_only_rows_matching_user_email(self):
        user = UserFactory(role="donor", email="alex@example.com")
        c = CampaignFactory()
        # Match → included.
        d_mine = DonationFactory(
            donor_email="alex@example.com",
            campaign=c,
            amount_cents=5_000,
            status="completed",
        )
        # Different donor → excluded.
        DonationFactory(
            donor_email="someone-else@example.com",
            campaign=c,
            amount_cents=9_999,
            status="completed",
        )

        rows = donor_history(user)
        ids = [d.id for d in rows]
        assert ids == [d_mine.id]

    def test_case_insensitive_email_match(self):
        """``Margaret@Example.com`` (donation row) matches
        ``margaret@example.com`` (user record).

        Donors type whatever capitalisation they like into the donate
        form; the User table is normalised. The service must bridge the
        gap so the donor never sees an empty history because of a stray
        capital letter.
        """
        user = UserFactory(role="donor", email="margaret@example.com")
        c = CampaignFactory()
        d_mixed = DonationFactory(
            donor_email="Margaret@Example.com",
            campaign=c,
            amount_cents=2_500,
            status="completed",
        )
        d_upper = DonationFactory(
            donor_email="MARGARET@EXAMPLE.COM",
            campaign=c,
            amount_cents=1_500,
            status="completed",
        )

        rows = donor_history(user)
        ids = sorted(d.id for d in rows)
        assert ids == sorted([d_mixed.id, d_upper.id])

    def test_returns_all_statuses_including_failed_and_cancelled(self):
        """Every status is returned — the template tags the bad ones.

        Hiding ``failed`` would leave a donor wondering why their bank
        statement shows nothing; surfacing it (with a status badge)
        lets them try again or contact support.
        """
        user = UserFactory(role="donor", email="grace@example.com")
        c = CampaignFactory()
        for status in (
            "pending",
            "completed",
            "failed",
            "refunded",
            "cancelled",
        ):
            DonationFactory(
                donor_email="grace@example.com",
                campaign=c,
                amount_cents=1_000,
                status=status,
            )

        rows = donor_history(user)
        assert len(rows) == 5
        assert {d.status for d in rows} == {
            "pending",
            "completed",
            "failed",
            "refunded",
            "cancelled",
        }

    def test_orders_newest_first(self):
        from django.utils import timezone

        user = UserFactory(role="donor", email="ordered@example.com")
        c = CampaignFactory()
        older = DonationFactory(
            donor_email="ordered@example.com",
            campaign=c,
            amount_cents=1_000,
            status="completed",
        )
        newer = DonationFactory(
            donor_email="ordered@example.com",
            campaign=c,
            amount_cents=2_000,
            status="completed",
        )
        # ``auto_now_add`` will stamp both ``now``; rewind the first
        # row deliberately so ordering is unambiguous.
        from apps.donations.models import Donation

        Donation.objects.filter(pk=older.pk).update(
            created_at=timezone.now().replace(year=2024, month=1, day=1)
        )

        rows = donor_history(user)
        assert [d.id for d in rows] == [newer.id, older.id]

    def test_empty_when_donor_has_no_donations(self):
        user = UserFactory(role="donor", email="new@example.com")
        assert donor_history(user) == []
