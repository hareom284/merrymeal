import pytest
from django.urls import reverse

from apps.accounts.models import Application
from apps.accounts.tests.factories import CityFactory, UserFactory
from apps.dietary.models import Allergy, DietPreference


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


def _login_admin(client):
    admin = UserFactory(email="admin@mm.com", role="admin")
    client.force_login(admin)
    return admin


def _login_member(client):
    member = UserFactory(email="member@mm.com", role="member")
    client.force_login(member)
    return member


# ---------- detail view ----------

def test_detail_renders_application_fields(client):
    app = _submitted_app()
    _login_admin(client)
    response = client.get(
        reverse("dashboards:admin_application_detail", args=[app.id])
    )
    assert response.status_code == 200
    assert b"Margaret W." in response.content
    assert b"12 Main St" in response.content


def test_detail_non_admin_gets_403(client):
    app = _submitted_app()
    _login_member(client)
    response = client.get(
        reverse("dashboards:admin_application_detail", args=[app.id])
    )
    assert response.status_code == 403


# ---------- approve POST ----------

def test_approve_post_creates_member_and_redirects(client):
    from django.core import mail
    app = _submitted_app()
    _login_admin(client)
    response = client.post(
        reverse("dashboards:admin_application_approve", args=[app.id])
    )
    assert response.status_code == 302
    assert response.url == reverse("dashboards:admin_applications")

    from apps.accounts.models import User
    assert User.objects.filter(email="margaret@example.com").exists()
    assert len(mail.outbox) == 1


# ---------- reject POST ----------

def test_reject_post_without_reason_re_renders_with_error(client):
    app = _submitted_app()
    _login_admin(client)
    response = client.post(
        reverse("dashboards:admin_application_reject", args=[app.id]),
        {},
    )
    assert response.status_code == 200
    assert b"Please provide a reason" in response.content


def test_reject_post_with_reason_marks_rejected_and_redirects(client):
    from django.core import mail
    app = _submitted_app()
    _login_admin(client)
    response = client.post(
        reverse("dashboards:admin_application_reject", args=[app.id]),
        {"reason": "Outside delivery area."},
    )
    assert response.status_code == 302
    assert response.url == reverse("dashboards:admin_applications")

    app.refresh_from_db()
    assert app.status == Application.STATUS_REJECTED
    assert len(mail.outbox) == 1
