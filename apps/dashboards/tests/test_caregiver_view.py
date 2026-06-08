"""Tests for the caregiver multi-member dashboard.

Story 3.8 — Caregiver multi-member view.

Note: the upstream spec relied on the `freezer` fixture from
pytest-freezer to pin "today" to 2026-06-15. That package is not yet
installed in this repo, so the fixture below seeds `MealPlan` rows with
`timezone.localdate()` instead — semantically equivalent for the assertions.
"""
from __future__ import annotations

import pytest
from django.utils import timezone

from apps.accounts.tests.factories import (
    MemberCaregiverLinkFactory,
    UserAddressFactory,
    UserFactory,
)
from apps.kitchens.tests.factories import KitchenFactory
from apps.meals.tests.factories import MealFactory
from apps.planning.tests.factories import MealPlanFactory


@pytest.fixture
def caregiver_with_members(db):
    today = timezone.localdate()
    caregiver = UserFactory(role="caregiver")
    kitchen = KitchenFactory(
        latitude=-37.81, longitude=144.96, service_radius_km=10
    )
    members = []
    for _ in range(3):
        m = UserFactory(role="member")
        UserAddressFactory(user=m, latitude=-37.82, longitude=144.97)
        MemberCaregiverLinkFactory(member=m, caregiver=caregiver)
        members.append(m)
    MealPlanFactory(
        kitchen=kitchen, meal=MealFactory(name="Today special"),
        service_date=today,
    )
    return caregiver, members


@pytest.mark.django_db
class TestCaregiverList:
    def test_zero_members_shows_empty_state(self, client, db):
        caregiver = UserFactory(role="caregiver")
        client.force_login(caregiver)
        resp = client.get("/dashboard/")
        assert resp.status_code == 200
        assert b"not linked to any members" in resp.content

    def test_three_members_render(self, client, caregiver_with_members):
        caregiver, _ = caregiver_with_members
        client.force_login(caregiver)
        resp = client.get("/dashboard/")
        assert resp.status_code == 200
        # 3 rows, one per linked member.
        assert resp.content.count(b'class="caregiver-row') == 3

    def test_query_budget(self, client, caregiver_with_members,
                          django_assert_max_num_queries):
        caregiver, _ = caregiver_with_members
        client.force_login(caregiver)
        # 2 + 2N base + slack for auth/session.
        with django_assert_max_num_queries(2 + 2 * 3 + 8):
            client.get("/dashboard/")

    def test_member_detail_renders_today_card(self, client,
                                              caregiver_with_members):
        caregiver, members = caregiver_with_members
        client.force_login(caregiver)
        target = members[0]
        resp = client.get(f"/dashboard/member/{target.pk}/")
        assert resp.status_code == 200
        assert b"Key ingredients" in resp.content

    def test_member_detail_forbidden_for_unlinked_member(self, client, db):
        caregiver = UserFactory(role="caregiver")
        stranger = UserFactory(role="member")
        client.force_login(caregiver)
        resp = client.get(f"/dashboard/member/{stranger.pk}/")
        assert resp.status_code in (403, 404)
