"""Story 6.1 — admin home aggregation service.

Pure-aggregation unit tests for the dashboard "what needs attention now"
service. The view layer in ``test_admin_home_view`` covers permissions
and HTMX partial rendering.
"""
from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.dashboards.services import admin_summary

# ---------- pure helpers ----------


def test_severity_green_when_zero():
    assert admin_summary.severity(0, threshold=5) == "green"


def test_severity_yellow_below_threshold():
    assert admin_summary.severity(1, threshold=5) == "yellow"
    assert admin_summary.severity(4, threshold=5) == "yellow"


def test_severity_red_at_or_above_threshold():
    assert admin_summary.severity(5, threshold=5) == "red"
    assert admin_summary.severity(99, threshold=5) == "red"


# ---------- build() shape ----------


@pytest.mark.django_db
def test_build_returns_five_cards_in_known_order():
    cards = admin_summary.build()
    titles = [c.title for c in cards]
    assert titles == [
        "Pending applications",
        "Expiring stock",
        "Failed deliveries today",
        "Unassigned deliveries today",
        "Recent food-safety failures",
    ]


@pytest.mark.django_db
def test_build_empty_dataset_returns_all_green():
    cards = admin_summary.build()
    assert all(c.count == 0 for c in cards)
    assert all(c.severity == "green" for c in cards)


@pytest.mark.django_db
def test_card_fields_are_shaped_correctly():
    cards = admin_summary.build()
    for c in cards:
        assert isinstance(c.title, str) and c.title
        assert isinstance(c.count, int)
        assert isinstance(c.link, str) and c.link
        assert c.severity in {"green", "yellow", "red"}
        assert isinstance(c.threshold, int) and c.threshold > 0


# ---------- per-card metrics ----------


@pytest.mark.django_db
def test_pending_applications_counts_only_submitted():
    from apps.accounts.models import Application

    Application.objects.create(
        full_name="Sub Person",
        email="sub@example.com",
        dob="1940-01-01",
        status=Application.STATUS_SUBMITTED,
    )
    Application.objects.create(
        full_name="Draft Person",
        email="draft@example.com",
        dob="1940-01-01",
        status=Application.STATUS_DRAFT,
    )
    Application.objects.create(
        full_name="Approved Person",
        email="approved@example.com",
        dob="1940-01-01",
        status=Application.STATUS_APPROVED,
    )

    cards = {c.title: c for c in admin_summary.build()}
    assert cards["Pending applications"].count == 1


@pytest.mark.django_db
def test_expiring_stock_counts_batches_within_window():
    from apps.kitchens.models import Ingredient, IngredientBatch, Kitchen

    kitchen = Kitchen.objects.create(
        name="Test Kitchen",
        latitude=Decimal("-37.80"),
        longitude=Decimal("144.96"),
    )
    ing = Ingredient.objects.create(name="Carrot", unit="kg")

    today = timezone.localdate()
    # within 3 days -> counted
    IngredientBatch.objects.create(
        ingredient=ing,
        kitchen=kitchen,
        quantity=Decimal("1.00"),
        expiration_date=today + timedelta(days=1),
    )
    IngredientBatch.objects.create(
        ingredient=ing,
        kitchen=kitchen,
        quantity=Decimal("1.00"),
        expiration_date=today + timedelta(days=3),
    )
    # outside window -> ignored
    IngredientBatch.objects.create(
        ingredient=ing,
        kitchen=kitchen,
        quantity=Decimal("1.00"),
        expiration_date=today + timedelta(days=30),
    )

    cards = {c.title: c for c in admin_summary.build()}
    assert cards["Expiring stock"].count == 2


@pytest.mark.django_db
def test_food_safety_failures_only_recent_24h():
    from apps.accounts.tests.factories import UserFactory
    from apps.food_safety.models import FoodSafetyCheck
    from apps.kitchens.models import Kitchen

    user = UserFactory(role="kitchen_staff")
    kitchen = Kitchen.objects.create(
        name="Test Kitchen",
        latitude=Decimal("-37.80"),
        longitude=Decimal("144.96"),
    )

    now = timezone.now()
    FoodSafetyCheck.objects.create(
        kitchen=kitchen,
        check_type=FoodSafetyCheck.CheckType.HYGIENE,
        result=FoodSafetyCheck.Result.FAIL,
        checked_by=user,
        checked_at=now - timedelta(hours=2),
    )
    FoodSafetyCheck.objects.create(
        kitchen=kitchen,
        check_type=FoodSafetyCheck.CheckType.HYGIENE,
        result=FoodSafetyCheck.Result.PASS,
        checked_by=user,
        checked_at=now - timedelta(hours=2),
    )
    # outside window -> ignored
    FoodSafetyCheck.objects.create(
        kitchen=kitchen,
        check_type=FoodSafetyCheck.CheckType.HYGIENE,
        result=FoodSafetyCheck.Result.FAIL,
        checked_by=user,
        checked_at=now - timedelta(days=2),
    )

    cards = {c.title: c for c in admin_summary.build()}
    assert cards["Recent food-safety failures"].count == 1


@pytest.mark.django_db
def test_pending_applications_severity_red_at_threshold():
    from apps.accounts.models import Application

    threshold = admin_summary._THRESHOLDS["pending_apps"]
    for i in range(threshold):
        Application.objects.create(
            full_name=f"Person {i}",
            email=f"p{i}@example.com",
            dob="1940-01-01",
            status=Application.STATUS_SUBMITTED,
        )

    cards = {c.title: c for c in admin_summary.build()}
    card = cards["Pending applications"]
    assert card.count == threshold
    assert card.severity == "red"
