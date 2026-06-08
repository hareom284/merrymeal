"""Tests for Story 5.8 — admin campaign-progress card.

Covers the progress aggregation service
(``apps.dashboards.services.campaign_progress``) plus the three views (index,
detail, CSV export) under ``/admin/campaigns/``. The aggregation lives in the
``dashboards`` app because ``dashboards`` is the top of the cross-app
dependency tree (see CLAUDE.md) and may freely import from ``donations``.

All money in the assertions below is integer cents on the way in, dollars on
the way out — the only conversion site is the ``dollars`` template tag (Story
5.1).
"""
import datetime as dt

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.dashboards.services.campaign_progress import (
    list_active_campaigns,
    progress_snapshot,
)
from apps.donations.tests.factories import CampaignFactory, DonationFactory

# ---------- progress-snapshot service ----------


@pytest.mark.django_db
def test_progress_snapshot_sums_completed_donations_only():
    c = CampaignFactory(goal_cents=10_000_00)
    DonationFactory(campaign=c, amount_cents=50_00, status="completed")
    DonationFactory(campaign=c, amount_cents=20_00, status="completed")
    DonationFactory(campaign=c, amount_cents=99_00, status="pending")  # excluded
    DonationFactory(campaign=c, amount_cents=10_00, status="refunded")  # excluded
    snap = progress_snapshot(c)
    assert snap.raised_cents == 7000
    # 70 / 100000 = 0.07 % → floored to 0
    assert snap.pct == 0
    assert snap.goal_cents == 1_000_000


@pytest.mark.django_db
def test_progress_caps_at_100_pct():
    c = CampaignFactory(goal_cents=10_00)
    DonationFactory(campaign=c, amount_cents=1_000_00, status="completed")
    assert progress_snapshot(c).pct == 100


@pytest.mark.django_db
def test_list_active_campaigns_excludes_inactive():
    CampaignFactory(name="Open", is_active=True)
    CampaignFactory(name="Closed", is_active=False)
    names = [s.campaign.name for s in list_active_campaigns()]
    assert names == ["Open"]


@pytest.mark.django_db
def test_days_remaining_clamped_to_zero(monkeypatch):
    # Pin "today" to 2026-06-02 (Australia/Melbourne) without depending on
    # pytest-freezer / freezegun (neither is installed and the project
    # forbids adding new packages mid-sprint). The service reaches for the
    # current local date via ``timezone.localdate()``; replacing that with
    # a constant is enough for a deterministic days-remaining computation.
    fixed_today = dt.date(2026, 6, 2)
    monkeypatch.setattr(
        "apps.dashboards.services.campaign_progress.timezone.localdate",
        lambda: fixed_today,
    )

    past = CampaignFactory(
        end_at=timezone.make_aware(dt.datetime(2026, 5, 31, 9, 0, 0))
    )
    future = CampaignFactory(
        end_at=timezone.make_aware(dt.datetime(2026, 6, 7, 9, 0, 0))
    )
    open_ended = CampaignFactory(end_at=None)
    assert progress_snapshot(past).days_remaining == 0
    assert progress_snapshot(future).days_remaining == 5
    assert progress_snapshot(open_ended).days_remaining is None


# ---------- view integration ----------


@pytest.fixture
def admin_user(django_user_model):
    return django_user_model.objects.create_superuser(
        email="admin@example.com",
        full_name="Admin",
        role="admin",
        password="x",
    )


@pytest.mark.django_db
def test_index_renders_active_campaigns_with_progress(client, admin_user):
    c = CampaignFactory(name="Winter", goal_cents=1000_00, is_active=True)
    DonationFactory(campaign=c, amount_cents=500_00, status="completed")
    CampaignFactory(name="Closed", is_active=False)
    client.force_login(admin_user)
    resp = client.get(reverse("dashboards_admin_campaigns:index"))
    assert resp.status_code == 200
    assert b"Winter" in resp.content
    assert b"Closed" not in resp.content
    assert b"$500.00" in resp.content
    assert b"50%" in resp.content


@pytest.mark.django_db
def test_non_admin_blocked(client, django_user_model):
    user = django_user_model.objects.create_user(
        email="m@example.com",
        full_name="M",
        role="member",
        password="x",
    )
    client.force_login(user)
    resp = client.get(reverse("dashboards_admin_campaigns:index"))
    assert resp.status_code in (302, 403)


@pytest.mark.django_db
def test_csv_export_streams_rows(client, admin_user):
    c = CampaignFactory(slug="winter")
    DonationFactory(
        campaign=c,
        donor_email="a@x.com",
        amount_cents=50_00,
        status="completed",
        transaction_id="cs_1",
        receipt_number="D2026-000001",
    )
    client.force_login(admin_user)
    resp = client.get(
        reverse("dashboards_admin_campaigns:export_csv", args=["winter"])
    )
    assert resp.status_code == 200
    body = b"".join(resp.streaming_content).decode()
    assert "donor_email" in body.splitlines()[0]
    assert "a@x.com" in body
    assert "50.00" in body
    assert "cs_1" in body
    assert "D2026-000001" in body
    assert resp["Content-Type"].startswith("text/csv")
    assert "winter-donations.csv" in resp["Content-Disposition"]


@pytest.mark.django_db
def test_detail_status_filter(client, admin_user):
    c = CampaignFactory(slug="winter")
    DonationFactory(campaign=c, status="completed", amount_cents=100)
    DonationFactory(campaign=c, status="refunded", amount_cents=200)
    client.force_login(admin_user)
    resp = client.get(
        reverse("dashboards_admin_campaigns:detail", args=["winter"]),
        {"status": "completed"},
    )
    assert resp.status_code == 200
    # The completed row + chip label both contain "completed" — that's at
    # least two hits when the filter matches.
    assert resp.content.count(b"completed") >= 2
    # The refunded donation row must NOT appear — the only legitimate
    # appearances of "refunded" in the page are the chip label and its
    # link href.
    assert b">refunded</td>" not in resp.content
    # The refunded donation's amount also must not appear in a row.
    assert b"$2.00" not in resp.content


@pytest.mark.django_db
def test_detail_paginates_donations(client, admin_user):
    c = CampaignFactory(slug="big")
    for _ in range(27):
        DonationFactory(campaign=c, status="completed", amount_cents=100)
    client.force_login(admin_user)
    resp = client.get(reverse("dashboards_admin_campaigns:detail", args=["big"]))
    assert resp.status_code == 200
    # Page 1 → "Next" link visible since 27 > 25.
    assert b"Next" in resp.content
    resp2 = client.get(
        reverse("dashboards_admin_campaigns:detail", args=["big"]),
        {"page": 2},
    )
    assert resp2.status_code == 200
    assert b"Prev" in resp2.content
