import pytest
from django.core import mail
from django.test import TestCase

from apps.accounts.models import Application, CaregiverLink, User
from apps.accounts.services.applications import approve_application, reject_application
from apps.accounts.tests.factories import CityFactory, UserFactory


pytestmark = pytest.mark.django_db(transaction=True)


def _submitted_app(**kwargs):
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


def _admin():
    return UserFactory(email="admin@example.com", role="admin")


# ---------- approve: basic ----------

def test_approve_creates_member_user():
    app = _submitted_app()
    admin = _admin()
    member = approve_application(app, admin)
    assert member.role == "member"
    assert member.email == "margaret@example.com"


def test_approve_marks_application_approved():
    app = _submitted_app()
    admin = _admin()
    approve_application(app, admin)
    app.refresh_from_db()
    assert app.status == Application.STATUS_APPROVED
    assert app.approved_by == admin.id


def test_approve_sends_welcome_email():
    app = _submitted_app()
    admin = _admin()
    approve_application(app, admin)
    assert len(mail.outbox) == 1
    msg = mail.outbox[0]
    assert "margaret@example.com" in msg.to
    assert "set your password" in msg.subject


def test_approve_welcome_email_contains_setup_link():
    app = _submitted_app()
    admin = _admin()
    approve_application(app, admin)
    body = mail.outbox[0].body
    assert "set-password" in body


def test_approve_raises_if_not_submitted():
    app = _submitted_app()
    app.status = Application.STATUS_DRAFT
    app.save()
    admin = _admin()
    with pytest.raises(ValueError, match="submitted"):
        approve_application(app, admin)


# ---------- approve: caregiver path ----------

def test_approve_creates_new_caregiver_user():
    app = _submitted_app(
        applying_for_other=True,
        caregiver_full_name="Jane C.",
        caregiver_email="jane@example.com",
        relationship="family",
    )
    admin = _admin()
    approve_application(app, admin)
    caregiver = User.objects.get(email="jane@example.com")
    assert caregiver.role == "caregiver"
    member = User.objects.get(email="margaret@example.com")
    link = CaregiverLink.objects.get(member=member, caregiver=caregiver)
    assert link.relationship == "family"


def test_approve_reuses_existing_caregiver():
    existing_cg = UserFactory(email="jane@example.com", role="caregiver")
    app = _submitted_app(
        applying_for_other=True,
        caregiver_full_name="Jane C.",
        caregiver_email="jane@example.com",
        relationship="friend",
    )
    admin = _admin()
    approve_application(app, admin)
    # No duplicate caregiver user created
    assert User.objects.filter(email="jane@example.com").count() == 1
    member = User.objects.get(email="margaret@example.com")
    link = CaregiverLink.objects.get(member=member, caregiver=existing_cg)
    assert link.relationship == "friend"


# ---------- reject ----------

def test_reject_marks_application_rejected():
    app = _submitted_app()
    admin = _admin()
    reject_application(app, admin, reason="Outside delivery area.")
    app.refresh_from_db()
    assert app.status == Application.STATUS_REJECTED
    assert "delivery area" in app.rejected_reason


def test_reject_sends_rejection_email():
    app = _submitted_app()
    admin = _admin()
    reject_application(app, admin, reason="Outside delivery area.")
    assert len(mail.outbox) == 1
    msg = mail.outbox[0]
    assert "margaret@example.com" in msg.to
    assert "Update on your MerryMeal application" in msg.subject


def test_reject_raises_if_reason_empty():
    app = _submitted_app()
    admin = _admin()
    with pytest.raises(ValueError, match="required"):
        reject_application(app, admin, reason="")
