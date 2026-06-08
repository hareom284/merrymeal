"""Tests for Story 6.3 — donor history view (``/donor/history/``).

The view is thin: gate on ``@role_required('donor')``, call the
service, render. The interesting assertions here are the role gate
(anonymous → login redirect; member/volunteer → 403) and the
data-isolation contract (a donor only sees rows whose
``donor_email`` matches their own user record).
"""
from __future__ import annotations

import pytest
from django.urls import reverse

from apps.accounts.tests.factories import UserFactory
from apps.donations.tests.factories import CampaignFactory, DonationFactory


@pytest.mark.django_db
class TestDonorHistoryViewAccess:
    def test_anonymous_is_redirected_to_login(self, client):
        response = client.get(reverse("dashboards:donor_history"))
        assert response.status_code == 302
        # ``role_required`` redirects to the accounts login URL.
        assert "/login" in response["Location"]

    def test_member_role_is_forbidden(self, client):
        u = UserFactory(role="member", email="m@example.com")
        client.force_login(u)
        response = client.get(reverse("dashboards:donor_history"))
        assert response.status_code == 403

    def test_volunteer_role_is_forbidden(self, client):
        u = UserFactory(role="volunteer", email="v@example.com")
        client.force_login(u)
        response = client.get(reverse("dashboards:donor_history"))
        assert response.status_code == 403

    def test_donor_role_can_load_page(self, client):
        u = UserFactory(role="donor", email="d@example.com")
        client.force_login(u)
        response = client.get(reverse("dashboards:donor_history"))
        assert response.status_code == 200


@pytest.mark.django_db
class TestDonorHistoryViewContent:
    def test_donor_sees_only_their_own_rows(self, client):
        me = UserFactory(role="donor", email="me@example.com")
        them = UserFactory(role="donor", email="them@example.com")
        c = CampaignFactory(name="Winter Appeal")
        mine = DonationFactory(
            donor_email=me.email,
            campaign=c,
            amount_cents=4_200,
            status="completed",
        )
        DonationFactory(
            donor_email=them.email,
            campaign=c,
            amount_cents=9_900,
            status="completed",
        )
        client.force_login(me)

        response = client.get(reverse("dashboards:donor_history"))
        assert response.status_code == 200
        donations = list(response.context["donations"])
        ids = [d.id for d in donations]
        assert ids == [mine.id]
        # Campaign name renders on the page.
        assert b"Winter Appeal" in response.content

    def test_empty_state_when_no_donations(self, client):
        u = UserFactory(role="donor", email="empty@example.com")
        client.force_login(u)

        response = client.get(reverse("dashboards:donor_history"))
        assert response.status_code == 200
        assert list(response.context["donations"]) == []
        # The template renders an empty-state message; the exact wording
        # is locked here so the design doesn't drift to a blank page
        # that confuses first-time donors.
        assert b"No donations yet" in response.content

    def test_case_insensitive_email_match_renders(self, client):
        """End-to-end check that the case-insensitive bridge works.

        Sprint 09's donate form preserves the donor's typed
        capitalisation; the User table normalises. The view must still
        surface the row.
        """
        u = UserFactory(role="donor", email="margaret@example.com")
        c = CampaignFactory()
        d = DonationFactory(
            donor_email="Margaret@Example.com",
            campaign=c,
            amount_cents=2_500,
            status="completed",
        )
        client.force_login(u)

        response = client.get(reverse("dashboards:donor_history"))
        assert response.status_code == 200
        ids = [row.id for row in response.context["donations"]]
        assert ids == [d.id]
