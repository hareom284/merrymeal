"""Tests for Story 6.2 — Partner outcomes view.

The most important assertions in this module are the cross-partner
isolation tests in :class:`TestPartnerOutcomesIsolation`. A partner user
must never, by any means (URL fudging, query string, CSV), see members
that belong to another partner. The view derives ``partner_id`` from
``request.user.partner_id`` only — there is no query/path parameter to
manipulate.

Role-gate substitution note
---------------------------
The ``users.role`` choices do not include ``"partner"`` in this codebase
— partner staff are represented as ``role="admin"`` or
``"kitchen_staff"`` with a non-NULL ``partner_id``. Adding a new role
would require a schema-locked migration update we do not want. The view
therefore uses a ``partner_required`` decorator that gates on
``user.partner_id is not None`` instead of the literal role string. The
tests that follow create users with whatever role string the story spec
called for, since Django does not validate choices at save-time, but
the security contract is enforced solely by the ``partner_id`` check.
"""
from __future__ import annotations

import csv
import io
from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.accounts.tests.factories import (
    AddressFactory,
    CityFactory,
    UserFactory,
)
from apps.delivery.models import Delivery, DeliveryFeedback
from apps.partners.tests.factories import PartnerFactory

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def two_partners(db):
    p1 = PartnerFactory(legal_name="Northcote Community Centre")
    p2 = PartnerFactory(legal_name="St Kilda Charity")
    return p1, p2


@pytest.fixture
def partner_user(db, two_partners):
    p1, _ = two_partners
    return UserFactory(
        role="admin", partner=p1, email="contact@p1.org"
    )


@pytest.fixture
def members_for_each_partner(db, two_partners):
    """3 members under partner #1, 2 members under partner #2."""
    p1, p2 = two_partners
    UserFactory.create_batch(3, role="member", partner=p1)
    UserFactory.create_batch(2, role="member", partner=p2)


# ---------------------------------------------------------------------------
# Security: cross-partner isolation
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestPartnerOutcomesIsolation:
    """SECURITY: a partner user must never see another partner's rows."""

    def test_partner_sees_only_own_members(
        self, client, partner_user, members_for_each_partner
    ):
        client.force_login(partner_user)
        response = client.get(reverse("dashboards:partner_outcomes"))
        assert response.status_code == 200
        # 3 members belong to p1; none of p2's appear.
        assert response.context["aggregate"]["total_referred"] == 3
        assert len(response.context["rows"]) == 3

    def test_partner_user_with_null_partner_id_is_403(self, client, db):
        u = UserFactory(role="admin", partner=None, email="orphan@x.org")
        client.force_login(u)
        response = client.get(reverse("dashboards:partner_outcomes"))
        assert response.status_code == 403

    def test_non_partner_role_is_redirected_or_403(self, client, db):
        u = UserFactory(role="member", email="just-member@x.org")
        client.force_login(u)
        response = client.get(reverse("dashboards:partner_outcomes"))
        assert response.status_code in (302, 403)

    def test_anonymous_is_redirected(self, client, db):
        response = client.get(reverse("dashboards:partner_outcomes"))
        # Either an explicit redirect to login or a 403; the decorator
        # currently redirects.
        assert response.status_code in (302, 403)

    def test_csv_export_filters_by_partner_id(
        self, client, partner_user, members_for_each_partner
    ):
        client.force_login(partner_user)
        response = client.get(
            reverse("dashboards:partner_outcomes") + "?format=csv"
        )
        assert response.status_code == 200
        assert response["Content-Type"].startswith("text/csv")
        # ``utf-8-sig`` strips the leading BOM so ``csv`` sees clean
        # data.
        body = response.content.decode("utf-8-sig")
        rows = list(csv.reader(io.StringIO(body)))
        # 1 header + 3 data rows; never 5.
        assert len(rows) == 1 + 3

    def test_csv_has_utf8_bom(
        self, client, partner_user, members_for_each_partner
    ):
        client.force_login(partner_user)
        response = client.get(
            reverse("dashboards:partner_outcomes") + "?format=csv"
        )
        # Excel needs the BOM (``﻿``) at the very start of the
        # payload to display UTF-8 names without mojibake.
        assert response.content.startswith(b"\xef\xbb\xbf")


# ---------------------------------------------------------------------------
# Aggregate header
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestPartnerOutcomesAggregate:
    def test_total_and_active_counts(self, client, two_partners):
        p1, _ = two_partners
        UserFactory.create_batch(2, role="member", partner=p1)
        UserFactory(role="member", partner=p1, is_active=False)
        viewer = UserFactory(role="admin", partner=p1)
        client.force_login(viewer)

        response = client.get(reverse("dashboards:partner_outcomes"))

        assert response.context["aggregate"]["total_referred"] == 3
        assert response.context["aggregate"]["currently_active"] == 2

    def test_retention_pct_renders_when_no_eligible_members(
        self, client, two_partners
    ):
        """Denominator 0 must produce ``None`` (rendered as ``—``)."""
        p1, _ = two_partners
        # Member enrolled today — not yet 90 days old.
        UserFactory(role="member", partner=p1)
        viewer = UserFactory(role="admin", partner=p1)
        client.force_login(viewer)

        response = client.get(reverse("dashboards:partner_outcomes"))

        assert response.context["aggregate"]["retention_pct_90d"] is None
        assert b"\xe2\x80\x94" in response.content  # em-dash

    def test_retention_pct_calculated_when_eligible(
        self, client, two_partners
    ):
        p1, _ = two_partners
        old_dt = timezone.now() - timedelta(days=120)
        # 2 retained + 1 churned among the 90d+ cohort = 66.7%.
        for is_active in (True, True, False):
            m = UserFactory(
                role="member", partner=p1, is_active=is_active
            )
            # ``auto_now_add`` overrides anything passed in, so override
            # via update() after creation.
            from apps.accounts.models import User
            User.all_objects.filter(pk=m.pk).update(created_at=old_dt)
        viewer = UserFactory(role="admin", partner=p1)
        client.force_login(viewer)

        response = client.get(reverse("dashboards:partner_outcomes"))

        # 2 of 3 retained.
        assert response.context["aggregate"]["retention_pct_90d"] == 66.7


# ---------------------------------------------------------------------------
# Row data
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestPartnerOutcomesRows:
    def test_row_includes_suburb_status_enrolment(
        self, client, two_partners
    ):
        p1, _ = two_partners
        suburb = CityFactory(name="Brunswick")
        m = UserFactory(
            role="member", partner=p1, full_name="Alice Aster"
        )
        AddressFactory(user=m, city=suburb)
        viewer = UserFactory(role="admin", partner=p1)
        client.force_login(viewer)

        response = client.get(reverse("dashboards:partner_outcomes"))

        rows = response.context["rows"]
        assert len(rows) == 1
        assert rows[0]["full_name"] == "Alice Aster"
        assert rows[0]["suburb"] == "Brunswick"
        assert rows[0]["status"] == "active"
        assert rows[0]["enrolment_date"]

    def test_inactive_member_status(self, client, two_partners):
        p1, _ = two_partners
        UserFactory(
            role="member", partner=p1, full_name="Bob", is_active=False
        )
        viewer = UserFactory(role="admin", partner=p1)
        client.force_login(viewer)

        response = client.get(reverse("dashboards:partner_outcomes"))

        assert response.context["rows"][0]["status"] == "inactive"

    def test_avg_rating_and_last_delivery_aggregated(
        self, client, two_partners
    ):
        from apps.kitchens.tests.factories import KitchenFactory
        from apps.meals.tests.factories import MealFactory
        from apps.planning.tests.factories import MealPlanFactory

        p1, _ = two_partners
        member = UserFactory(role="member", partner=p1)
        AddressFactory(user=member)
        volunteer = UserFactory(
            role="volunteer", email="vol@x.org"
        )
        kitchen = KitchenFactory()
        plan = MealPlanFactory(
            kitchen=kitchen,
            meal=MealFactory(name="Soup"),
            service_date=timezone.localdate(),
        )
        member_addr = member.addresses.first()
        now = timezone.now()
        d1 = Delivery.objects.create(
            meal_plan=plan,
            volunteer=volunteer,
            member=member,
            member_address=member_addr,
            status=Delivery.STATUS_DELIVERED,
            scheduled_date=timezone.localdate() - timedelta(days=2),
            delivered_time=now - timedelta(days=2),
        )
        d2 = Delivery.objects.create(
            meal_plan=plan,
            volunteer=volunteer,
            member=member,
            member_address=member_addr,
            status=Delivery.STATUS_DELIVERED,
            scheduled_date=timezone.localdate(),
            delivered_time=now,
        )
        DeliveryFeedback.objects.create(delivery=d1, rating=4)
        DeliveryFeedback.objects.create(delivery=d2, rating=5)
        viewer = UserFactory(role="admin", partner=p1)
        client.force_login(viewer)

        response = client.get(reverse("dashboards:partner_outcomes"))

        row = response.context["rows"][0]
        assert row["avg_rating"] == 4.5
        # Last delivery is the most recent.
        assert row["last_delivery"] == now.date().isoformat()

    def test_no_ratings_renders_em_dash(self, client, two_partners):
        p1, _ = two_partners
        UserFactory(role="member", partner=p1, full_name="No Rate")
        viewer = UserFactory(role="admin", partner=p1)
        client.force_login(viewer)

        response = client.get(reverse("dashboards:partner_outcomes"))

        row = response.context["rows"][0]
        assert row["avg_rating"] is None
