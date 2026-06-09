"""Tests for the admin operational snapshot."""
import datetime as dt

import pytest

from apps.accounts.models import Application
from apps.accounts.tests.factories import CityFactory, UserFactory
from apps.ai_assistant.services.admin_context import build_admin_context
from apps.delivery.models import Delivery
from apps.delivery.tests.factories import DeliveryFactory


@pytest.mark.django_db
def test_admin_context_starts_with_admin_name():
    admin = UserFactory(role="admin", full_name="Alex Admin")
    snapshot = build_admin_context(admin)
    assert snapshot.startswith("Admin name: Alex Admin")


@pytest.mark.django_db
def test_admin_context_reports_pending_application_count():
    admin = UserFactory(role="admin")
    city = CityFactory()
    Application.objects.create(
        full_name="Margaret W.",
        email="m@example.com",
        dob="1940-01-01",
        status=Application.STATUS_SUBMITTED,
        address_label="Home",
        street="12 Main St",
        postal_code="3000",
        city_id=city.id,
    )
    snapshot = build_admin_context(admin)
    assert "Pending applications awaiting review: 1" in snapshot


@pytest.mark.django_db
def test_admin_context_reports_failed_deliveries_today():
    admin = UserFactory(role="admin")
    DeliveryFactory(
        scheduled_date=dt.date.today(),
        status=Delivery.STATUS_FAILED,
    )
    DeliveryFactory(
        scheduled_date=dt.date.today(),
        status=Delivery.STATUS_FAILED,
    )
    snapshot = build_admin_context(admin)
    assert "Failed deliveries today: 2" in snapshot


@pytest.mark.django_db
def test_admin_context_handles_empty_state():
    admin = UserFactory(role="admin")
    snapshot = build_admin_context(admin)
    assert "Pending applications awaiting review: 0" in snapshot
    assert "Failed deliveries today: 0" in snapshot
    assert "Ingredient batches expiring within 3 days: 0" in snapshot
