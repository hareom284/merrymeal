import pytest
from django.core import mail

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


# ---------- approve: atomicity ----------

def test_approve_rolls_back_on_inner_failure(monkeypatch):
    """A failure inside the atomic block reverts every write and skips email.

    Patches ``issue_password_setup_token`` (the last call inside the
    ``transaction.atomic()`` block) to raise. After the exception:
      * no member ``User`` row was committed
      * the application stays ``STATUS_SUBMITTED``
      * no welcome email is sent (``on_commit`` callback never fires)
    """
    import apps.accounts.services.tokens as tokens

    def _boom(_member):
        raise RuntimeError("token issuance failed")

    # The service imports ``issue_password_setup_token`` lazily inside
    # the function body, so we patch the source module — the next call
    # picks up the patched attribute.
    monkeypatch.setattr(tokens, "issue_password_setup_token", _boom)

    app = _submitted_app()
    admin = _admin()

    with pytest.raises(RuntimeError, match="token issuance failed"):
        approve_application(app, admin)

    assert not User.objects.filter(email="margaret@example.com").exists()
    app.refresh_from_db()
    assert app.status == Application.STATUS_SUBMITTED
    assert app.approved_by is None
    assert mail.outbox == []


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
