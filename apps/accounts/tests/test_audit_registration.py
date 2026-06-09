"""Verify ``User`` and ``Application`` are registered with django-auditlog
and that the approve / reject services produce ``LogEntry`` rows.

Without registration the ``set_actor(admin_user)`` context manager in
``apps.accounts.services.applications`` is a silent no-op — the audit
viewer (Story 6.6) then returns an empty result for every
member-approval history. These tests are the regression gate that
caught the bug (audit handoff P0-2).
"""
import pytest
from auditlog.models import LogEntry
from auditlog.registry import auditlog

from apps.accounts.models import Application, User
from apps.accounts.services.applications import (
    approve_application,
    reject_application,
)
from apps.accounts.tests.factories import CityFactory, UserFactory

pytestmark = pytest.mark.django_db(transaction=True)


def _submitted_app(**kwargs) -> Application:
    city = CityFactory()
    defaults = dict(
        full_name="Margaret W.",
        email="margaret@example.com",
        dob="1940-01-01",
        status=Application.STATUS_SUBMITTED,
        address_label="Home",
        street="12 Main St",
        postal_code="3000",
        city_id=city.id,
    )
    defaults.update(kwargs)
    return Application.objects.create(**defaults)


def _admin() -> User:
    return UserFactory(email="admin@example.com", role="admin")


# ---------- registration ----------


def test_application_is_registered_with_auditlog():
    assert auditlog.contains(Application)


def test_user_is_registered_with_auditlog():
    assert auditlog.contains(User)


# ---------- approve writes LogEntry rows ----------


def test_approve_writes_application_audit_log_with_admin_actor():
    app = _submitted_app()
    admin = _admin()

    before = LogEntry.objects.filter(
        content_type__app_label="accounts",
        content_type__model="application",
        object_id=str(app.id),
    ).count()

    approve_application(app, admin)

    entries = LogEntry.objects.filter(
        content_type__app_label="accounts",
        content_type__model="application",
        object_id=str(app.id),
    )
    assert entries.count() > before
    assert entries.filter(actor=admin).exists()


def test_approve_writes_user_audit_log_for_new_member():
    app = _submitted_app()
    admin = _admin()
    member = approve_application(app, admin)

    user_entries = LogEntry.objects.filter(
        content_type__app_label="accounts",
        content_type__model="user",
        object_id=str(member.id),
    )
    assert user_entries.exists()
    assert user_entries.filter(actor=admin).exists()


# ---------- reject writes LogEntry rows ----------


def test_reject_writes_application_audit_log_with_admin_actor():
    app = _submitted_app()
    admin = _admin()

    reject_application(app, admin, reason="Outside delivery area.")

    entries = LogEntry.objects.filter(
        content_type__app_label="accounts",
        content_type__model="application",
        object_id=str(app.id),
        actor=admin,
    )
    assert entries.exists()
