"""Tests for Story 6.4 — Tax receipt (FY) printer-friendly page.

The receipt page lists every ``completed`` donation a donor made within
one Australian financial year. The DoD spec lives in
``docs/product/sprints/sprint-10/stories/6.4-tax-receipt.md`` and is
tested here on three axes:

1. **FY helpers** — ``fy_period(2026)`` is ``(2025-07-01, 2026-06-30)``;
   ``is_valid_fy`` allows roughly 2024..(today's FY + 1).
2. **Boundary correctness** — donations stamped at ``23:59:59`` on
   ``30 June`` (Melbourne) belong to the closing FY; donations stamped
   at ``00:00:00`` on ``1 July`` belong to the next FY. The view uses
   ``created_at__date__gte/lte`` which evaluates in the project TZ
   (``Australia/Melbourne``), so UTC-naïve callers cannot drift the
   boundary by a day.
3. **JSON contract** — accountants ingest the ``?format=json`` response.
   The shape is locked: ``fy``, ``period``, ``donor``, ``donations``,
   ``total_cents``, ``charity``.

Why the donor identity bridge is ``donor_email`` (not ``donor_id``)
-------------------------------------------------------------------
``donations.donor_id`` is nullable (Story 5.2): anonymous donate-form
submissions land in the table without a User row, and are back-linked
later if/when an account is created with the same email. To match the
donor-history service (Story 6.3) the FY receipt also filters on
``donor_email__iexact`` so a logged-in donor sees every gift they ever
made under that address — including the ones submitted while logged
out.
"""
from __future__ import annotations

import json
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
from django.urls import reverse

from apps.accounts.tests.factories import UserFactory
from apps.dashboards.services import fy as fy_service
from apps.donations.models import Donation
from apps.donations.tests.factories import CampaignFactory, DonationFactory

MEL = ZoneInfo("Australia/Melbourne")


@pytest.fixture
def donor(db):
    return UserFactory(
        role="donor", email="alex@example.com", full_name="Alex Donor"
    )


class TestFYHelpers:
    """Pure unit tests — no DB, no client. ``fy_period`` and
    ``is_valid_fy`` are deliberately tiny so the boundary tests below
    can rely on them as ground truth."""

    def test_fy_period_2026(self):
        start, end = fy_service.fy_period(2026)
        assert start.isoformat() == "2025-07-01"
        assert end.isoformat() == "2026-06-30"

    def test_fy_period_2024(self):
        start, end = fy_service.fy_period(2024)
        assert start.isoformat() == "2023-07-01"
        assert end.isoformat() == "2024-06-30"

    @pytest.mark.parametrize(
        "fy,ok",
        [
            (2024, True),
            (2025, True),
            (2026, True),
            (1999, False),
            (3000, False),
            (2023, False),
        ],
    )
    def test_is_valid_fy(self, fy, ok):
        assert fy_service.is_valid_fy(fy) == ok


@pytest.mark.django_db
class TestFYReceiptViewAccess:
    """``@role_required('donor')`` mirrors Story 6.3's donor history
    view — anonymous redirects to login, non-donor roles get 403."""

    def test_anonymous_is_redirected_to_login(self, client):
        url = reverse("dashboards:donor_fy_receipt", args=[2026])
        response = client.get(url)
        assert response.status_code == 302
        assert "/login" in response["Location"]

    def test_member_role_is_forbidden(self, client):
        u = UserFactory(role="member", email="m@example.com")
        client.force_login(u)
        url = reverse("dashboards:donor_fy_receipt", args=[2026])
        assert client.get(url).status_code == 403

    def test_volunteer_role_is_forbidden(self, client):
        u = UserFactory(role="volunteer", email="v@example.com")
        client.force_login(u)
        url = reverse("dashboards:donor_fy_receipt", args=[2026])
        assert client.get(url).status_code == 403

    def test_donor_role_can_load_page(self, client, donor):
        client.force_login(donor)
        url = reverse("dashboards:donor_fy_receipt", args=[2026])
        assert client.get(url).status_code == 200


@pytest.mark.django_db
class TestFYReceiptBoundaries:
    """The two cases below pin the most-asked-about behaviour of this
    page: a donation at the last second of 30 June belongs to the
    closing FY; the first second of 1 July belongs to the next."""

    def test_fy_boundary_june_30_inclusive(self, client, donor):
        c = CampaignFactory()
        d = DonationFactory(
            donor_email=donor.email,
            campaign=c,
            amount_cents=1000,
            status="completed",
        )
        # last second of FY 2025 in Melbourne time
        Donation.objects.filter(pk=d.pk).update(
            created_at=datetime(2025, 6, 30, 23, 59, 59, tzinfo=MEL)
        )
        client.force_login(donor)

        r25 = client.get(
            reverse("dashboards:donor_fy_receipt", args=[2025])
        )
        assert r25.status_code == 200
        assert r25.context["total_cents"] == 1000

        r26 = client.get(
            reverse("dashboards:donor_fy_receipt", args=[2026])
        )
        assert r26.status_code == 200
        assert r26.context["total_cents"] == 0

    def test_fy_boundary_july_1_belongs_to_next_fy(self, client, donor):
        c = CampaignFactory()
        d = DonationFactory(
            donor_email=donor.email,
            campaign=c,
            amount_cents=2000,
            status="completed",
        )
        Donation.objects.filter(pk=d.pk).update(
            created_at=datetime(2025, 7, 1, 0, 0, 0, tzinfo=MEL)
        )
        client.force_login(donor)

        r26 = client.get(
            reverse("dashboards:donor_fy_receipt", args=[2026])
        )
        assert r26.status_code == 200
        assert r26.context["total_cents"] == 2000

        r25 = client.get(
            reverse("dashboards:donor_fy_receipt", args=[2025])
        )
        assert r25.status_code == 200
        assert r25.context["total_cents"] == 0


@pytest.mark.django_db
class TestFYReceiptFilters:
    def test_only_completed_status_counts(self, client, donor):
        """Non-``completed`` donations are not income for the donor;
        they cannot be receipted. Listing them would muddy the tax
        return."""
        c = CampaignFactory()
        for status in ("pending", "failed", "refunded", "cancelled"):
            d = DonationFactory(
                donor_email=donor.email,
                campaign=c,
                amount_cents=3000,
                status=status,
            )
            Donation.objects.filter(pk=d.pk).update(
                created_at=datetime(2025, 9, 1, 12, 0, tzinfo=MEL)
            )
        # The one that does count.
        ok = DonationFactory(
            donor_email=donor.email,
            campaign=c,
            amount_cents=7700,
            status="completed",
        )
        Donation.objects.filter(pk=ok.pk).update(
            created_at=datetime(2025, 9, 1, 12, 0, tzinfo=MEL)
        )

        client.force_login(donor)
        r = client.get(reverse("dashboards:donor_fy_receipt", args=[2026]))
        assert r.context["total_cents"] == 7700
        rows = list(r.context["rows"])
        assert len(rows) == 1
        assert rows[0]["amount_cents"] == 7700

    def test_donor_does_not_see_other_donors_rows(self, client, donor):
        """Email-isolation — mirrors the Story 6.3 contract. Cross-
        donor leakage at tax time would be a privacy breach."""
        c = CampaignFactory()
        mine = DonationFactory(
            donor_email=donor.email,
            campaign=c,
            amount_cents=4_200,
            status="completed",
        )
        Donation.objects.filter(pk=mine.pk).update(
            created_at=datetime(2025, 9, 1, 12, 0, tzinfo=MEL)
        )
        theirs = DonationFactory(
            donor_email="someone-else@example.com",
            campaign=c,
            amount_cents=99_999,
            status="completed",
        )
        Donation.objects.filter(pk=theirs.pk).update(
            created_at=datetime(2025, 9, 1, 12, 0, tzinfo=MEL)
        )
        client.force_login(donor)

        r = client.get(reverse("dashboards:donor_fy_receipt", args=[2026]))
        ids = [row["id"] for row in r.context["rows"]]
        assert ids == [mine.id]
        assert r.context["total_cents"] == 4_200

    def test_case_insensitive_email_match(self, client, donor):
        """Donors who typed mixed-case on the donate form still appear
        — Sprint 09 preserves the typed string."""
        c = CampaignFactory()
        d = DonationFactory(
            donor_email="ALEX@Example.com",
            campaign=c,
            amount_cents=5_500,
            status="completed",
        )
        Donation.objects.filter(pk=d.pk).update(
            created_at=datetime(2025, 12, 1, 12, 0, tzinfo=MEL)
        )
        client.force_login(donor)

        r = client.get(reverse("dashboards:donor_fy_receipt", args=[2026]))
        ids = [row["id"] for row in r.context["rows"]]
        assert ids == [d.id]


@pytest.mark.django_db
class TestFYReceiptValidation:
    def test_invalid_fy_404(self, client, donor):
        client.force_login(donor)
        r = client.get(
            reverse("dashboards:donor_fy_receipt", args=[1999])
        )
        assert r.status_code == 404

    def test_future_fy_404(self, client, donor):
        """A donor cannot ask for a receipt for an FY that has not
        started yet. ``is_valid_fy`` caps at ``this_fy + 1``."""
        client.force_login(donor)
        r = client.get(
            reverse("dashboards:donor_fy_receipt", args=[3000])
        )
        assert r.status_code == 404


@pytest.mark.django_db
class TestFYReceiptJSON:
    def test_json_response_shape(self, client, donor):
        c = CampaignFactory(name="Winter Appeal")
        d = DonationFactory(
            donor_email=donor.email,
            campaign=c,
            amount_cents=4500,
            status="completed",
        )
        Donation.objects.filter(pk=d.pk).update(
            created_at=datetime(2025, 10, 1, 12, 0, tzinfo=MEL)
        )
        client.force_login(donor)

        url = (
            reverse("dashboards:donor_fy_receipt", args=[2026])
            + "?format=json"
        )
        response = client.get(url)
        assert response.status_code == 200
        body = json.loads(response.content)
        assert body["fy"] == 2026
        assert body["period"] == {
            "start": "2025-07-01",
            "end": "2026-06-30",
        }
        assert body["donor"]["email"] == donor.email
        assert body["donor"]["name"] == donor.full_name
        assert body["total_cents"] == 4500
        assert body["charity"]["abn"]
        assert body["charity"]["address"]
        assert isinstance(body["donations"], list)
        assert len(body["donations"]) == 1
        row = body["donations"][0]
        assert row["amount_cents"] == 4500
        assert row["campaign"] == "Winter Appeal"
        assert row["date"] == "2025-10-01"

    def test_json_empty_fy_still_valid_shape(self, client, donor):
        client.force_login(donor)
        url = (
            reverse("dashboards:donor_fy_receipt", args=[2026])
            + "?format=json"
        )
        body = json.loads(client.get(url).content)
        assert body["total_cents"] == 0
        assert body["donations"] == []


@pytest.mark.django_db
class TestFYReceiptTemplate:
    def test_renders_total_and_abn(self, client, donor):
        c = CampaignFactory(name="Winter Appeal")
        d = DonationFactory(
            donor_email=donor.email,
            campaign=c,
            amount_cents=12_345,
            status="completed",
        )
        Donation.objects.filter(pk=d.pk).update(
            created_at=datetime(2025, 8, 15, 9, 0, tzinfo=MEL)
        )
        client.force_login(donor)
        r = client.get(reverse("dashboards:donor_fy_receipt", args=[2026]))
        body = r.content.decode()
        # Total renders via the existing ``dollars`` filter.
        assert "$123.45" in body
        # Campaign name shows in the table.
        assert "Winter Appeal" in body
        # ABN footer is present (the actual value comes from settings;
        # the placeholder default contains digits and spaces).
        assert "ABN" in body
        # The print stylesheet must be linked at media="print" so the
        # browser only pulls it when the user opens print preview.
        assert 'media="print"' in body or "@media print" in body
