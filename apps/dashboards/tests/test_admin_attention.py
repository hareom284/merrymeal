"""Admin attention list views — click-through targets for the home cards.

Each view backs one card on ``dashboards:admin_home``. The tests below
exercise three concerns per view:

* RBAC — only ``role="admin"`` may load the page.
* Matching rows show up; non-matching rows are excluded.
* The URL reverses by name AND ``admin_summary.build()`` returns a real
  link (not the ``"#"`` fallback that the ``NoReverseMatch`` guard
  produces when a card's destination route is missing).
"""
from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.accounts.tests.factories import UserFactory
from apps.dashboards.services import admin_summary
from apps.delivery.models import Delivery
from apps.delivery.tests.factories import DeliveryFactory, RouteFactory
from apps.food_safety.models import FoodSafetyCheck
from apps.food_safety.tests.factories import FoodSafetyCheckFactory
from apps.kitchens.tests.factories import (
    IngredientBatchFactory,
    IngredientFactory,
    KitchenFactory,
)

pytestmark = pytest.mark.django_db


def _admin(client):
    user = UserFactory(email="attn-admin@example.com", role="admin")
    client.force_login(user)
    return user


def _member(client):
    user = UserFactory(email="attn-member@example.com", role="member")
    client.force_login(user)
    return user


# ---------- expiring stock ----------


def test_expiring_stock_forbidden_for_non_admin(client):
    _member(client)
    response = client.get(reverse("dashboards:expiring_stock"))
    assert response.status_code == 403


def test_expiring_stock_empty_renders_empty_state(client):
    _admin(client)
    response = client.get(reverse("dashboards:expiring_stock"))
    assert response.status_code == 200
    assert b"No batches expiring" in response.content


def test_expiring_stock_shows_matching_excludes_non_matching(client):
    today = timezone.localdate()
    kitchen = KitchenFactory()
    soon_ingredient = IngredientFactory(name="SoonCarrot")
    later_ingredient = IngredientFactory(name="LaterPotato")

    IngredientBatchFactory(
        ingredient=soon_ingredient,
        kitchen=kitchen,
        expiration_date=today + timedelta(days=1),
    )
    IngredientBatchFactory(
        ingredient=later_ingredient,
        kitchen=kitchen,
        expiration_date=today + timedelta(days=30),
    )

    _admin(client)
    response = client.get(reverse("dashboards:expiring_stock"))
    assert response.status_code == 200
    assert b"SoonCarrot" in response.content
    assert b"LaterPotato" not in response.content


def test_expiring_stock_reverse_and_card_link_resolve():
    url = reverse("dashboards:expiring_stock")
    assert url.endswith("/attention/expiring-stock/")

    cards = {c.title: c for c in admin_summary.build()}
    assert cards["Expiring stock"].link == url
    assert cards["Expiring stock"].link != "#"


# ---------- failed deliveries today ----------


def test_failed_deliveries_forbidden_for_non_admin(client):
    _member(client)
    response = client.get(reverse("dashboards:failed_deliveries_today"))
    assert response.status_code == 403


def test_failed_deliveries_empty_renders_empty_state(client):
    _admin(client)
    response = client.get(reverse("dashboards:failed_deliveries_today"))
    assert response.status_code == 200
    assert b"No failed deliveries today" in response.content


def test_failed_deliveries_shows_matching_excludes_non_matching(client):
    today = timezone.localdate()

    DeliveryFactory(
        member=UserFactory(email="failed@ex.com", full_name="Failed Today Member", role="member"),
        status=Delivery.STATUS_FAILED,
        scheduled_date=today,
        failure_reason="left_at_door: no answer",
    )
    # Wrong date — should be hidden.
    DeliveryFactory(
        member=UserFactory(email="yesterday@ex.com", full_name="Yesterday Member", role="member"),
        status=Delivery.STATUS_FAILED,
        scheduled_date=today - timedelta(days=1),
    )
    # Wrong status — should be hidden.
    DeliveryFactory(
        member=UserFactory(email="delivered@ex.com", full_name="Delivered Member", role="member"),
        status=Delivery.STATUS_DELIVERED,
        scheduled_date=today,
    )

    _admin(client)
    response = client.get(reverse("dashboards:failed_deliveries_today"))
    assert response.status_code == 200
    assert b"Failed Today Member" in response.content
    assert b"Yesterday Member" not in response.content
    assert b"Delivered Member" not in response.content


def test_failed_deliveries_reverse_and_card_link_resolve():
    url = reverse("dashboards:failed_deliveries_today")
    assert url.endswith("/attention/failed-deliveries/")

    cards = {c.title: c for c in admin_summary.build()}
    assert cards["Failed deliveries today"].link == url
    assert cards["Failed deliveries today"].link != "#"


# ---------- unassigned deliveries today ----------


def test_unassigned_deliveries_forbidden_for_non_admin(client):
    _member(client)
    response = client.get(reverse("dashboards:unassigned_deliveries_today"))
    assert response.status_code == 403


def test_unassigned_deliveries_empty_renders_empty_state(client):
    _admin(client)
    response = client.get(reverse("dashboards:unassigned_deliveries_today"))
    assert response.status_code == 200
    assert b"No unassigned deliveries today" in response.content


def test_unassigned_deliveries_shows_matching_excludes_non_matching(client):
    today = timezone.localdate()

    DeliveryFactory(
        member=UserFactory(email="unassigned@ex.com", full_name="Unassigned Member", role="member"),
        status=Delivery.STATUS_PENDING,
        scheduled_date=today,
        route=None,
    )
    # Has a route — already assigned.
    DeliveryFactory(
        member=UserFactory(email="routed@ex.com", full_name="Routed Member", role="member"),
        status=Delivery.STATUS_PENDING,
        scheduled_date=today,
        route=RouteFactory(),
    )

    # Wrong status (already out for delivery) — should be hidden.
    DeliveryFactory(
        member=UserFactory(email="outfor@ex.com", full_name="OutFor Member", role="member"),
        status=Delivery.STATUS_OUT_FOR_DELIVERY,
        scheduled_date=today,
        route=None,
    )

    _admin(client)
    response = client.get(reverse("dashboards:unassigned_deliveries_today"))
    assert response.status_code == 200
    assert b"Unassigned Member" in response.content
    assert b"Routed Member" not in response.content
    assert b"OutFor Member" not in response.content


def test_unassigned_deliveries_reverse_and_card_link_resolve():
    url = reverse("dashboards:unassigned_deliveries_today")
    assert url.endswith("/attention/unassigned-deliveries/")

    cards = {c.title: c for c in admin_summary.build()}
    assert cards["Unassigned deliveries today"].link == url
    assert cards["Unassigned deliveries today"].link != "#"


# ---------- recent food-safety failures ----------


def test_fs_failures_forbidden_for_non_admin(client):
    _member(client)
    response = client.get(reverse("dashboards:fs_failures_recent"))
    assert response.status_code == 403


def test_fs_failures_empty_renders_empty_state(client):
    _admin(client)
    response = client.get(reverse("dashboards:fs_failures_recent"))
    assert response.status_code == 200
    assert b"No food-safety failures" in response.content


def test_fs_failures_shows_matching_excludes_non_matching(client):
    now = timezone.now()
    kitchen_recent = KitchenFactory(name="RecentKitchen")
    kitchen_old = KitchenFactory(name="OldKitchen")
    kitchen_passed = KitchenFactory(name="PassedKitchen")
    staff = UserFactory(email="fs-staff@ex.com", role="kitchen_staff")

    FoodSafetyCheckFactory(
        kitchen=kitchen_recent,
        checked_by=staff,
        result=FoodSafetyCheck.Result.FAIL,
        checked_at=now - timedelta(hours=2),
        temperature_celsius=Decimal("12.00"),
    )
    # Too old — outside 24h.
    FoodSafetyCheckFactory(
        kitchen=kitchen_old,
        checked_by=staff,
        result=FoodSafetyCheck.Result.FAIL,
        checked_at=now - timedelta(days=2),
        temperature_celsius=Decimal("12.00"),
    )
    # Recent but passed.
    FoodSafetyCheckFactory(
        kitchen=kitchen_passed,
        checked_by=staff,
        result=FoodSafetyCheck.Result.PASS,
        checked_at=now - timedelta(hours=1),
        temperature_celsius=Decimal("4.00"),
    )

    _admin(client)
    response = client.get(reverse("dashboards:fs_failures_recent"))
    assert response.status_code == 200
    assert b"RecentKitchen" in response.content
    assert b"OldKitchen" not in response.content
    assert b"PassedKitchen" not in response.content


def test_fs_failures_reverse_and_card_link_resolve():
    url = reverse("dashboards:fs_failures_recent")
    assert url.endswith("/attention/food-safety-failures/")

    cards = {c.title: c for c in admin_summary.build()}
    assert cards["Recent food-safety failures"].link == url
    assert cards["Recent food-safety failures"].link != "#"


# ---------- end-to-end: all five cards now click through ----------


def test_admin_summary_build_returns_no_dead_links():
    """After wiring the four new routes, every card on the admin home
    must resolve to a real URL (no NoReverseMatch fallback).
    """
    cards = admin_summary.build()
    assert len(cards) == 5
    dead = [c.title for c in cards if c.link == "#"]
    assert dead == [], f"cards still falling back to '#': {dead}"


