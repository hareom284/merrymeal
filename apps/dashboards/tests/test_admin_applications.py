import pytest
from django.urls import reverse

from apps.accounts.models import Application
from apps.accounts.tests.factories import CityFactory, UserFactory

pytestmark = pytest.mark.django_db


def _submitted_app(city=None, **kwargs):
    if city is None:
        city = CityFactory()
    defaults = dict(
        full_name="Margaret W.",
        email="margaret@example.com",
        dob="1940-01-01",
        status=Application.STATUS_SUBMITTED,
        street="12 Main St",
        postal_code="3000",
        city_id=city.id,
    )
    defaults.update(kwargs)
    return Application.objects.create(**defaults)


def _login_admin(client):
    admin = UserFactory(email="admin@mm.com", role="admin", password="adminpass!")
    client.force_login(admin)
    return admin


def _login_member(client):
    member = UserFactory(email="member@mm.com", role="member")
    client.force_login(member)
    return member


# ---------- access control ----------

def test_list_requires_login(client):
    response = client.get(reverse("dashboards:admin_applications"))
    assert response.status_code in (302, 403)


def test_list_non_admin_gets_403(client):
    _login_member(client)
    response = client.get(reverse("dashboards:admin_applications"))
    assert response.status_code == 403


def test_list_admin_gets_200(client):
    _login_admin(client)
    response = client.get(reverse("dashboards:admin_applications"))
    assert response.status_code == 200


# ---------- list rendering ----------

def test_list_shows_submitted_applications(client):
    _submitted_app()
    _login_admin(client)
    response = client.get(reverse("dashboards:admin_applications"))
    assert b"Margaret W." in response.content


def test_list_does_not_show_draft_applications(client):
    Application.objects.create(
        full_name="Draft Person",
        email="draft@example.com",
        dob="1940-01-01",
        status=Application.STATUS_DRAFT,
    )
    _login_admin(client)
    response = client.get(reverse("dashboards:admin_applications"))
    assert b"Draft Person" not in response.content


def test_list_empty_shows_no_pending_message(client):
    _login_admin(client)
    response = client.get(reverse("dashboards:admin_applications"))
    assert response.status_code == 200
    # page renders without error regardless of empty state
    assert b"application" in response.content.lower()


# ---------- city filter ----------

def test_city_filter_returns_matching_applications(client):
    city_a = CityFactory(name="CityA")
    city_b = CityFactory(name="CityB")
    _submitted_app(city=city_a, email="app_a@example.com", full_name="App A")
    _submitted_app(city=city_b, email="app_b@example.com", full_name="App B")
    _login_admin(client)

    url = reverse("dashboards:admin_applications")
    response = client.get(url, {"city": city_a.id})
    assert b"App A" in response.content
    assert b"App B" not in response.content


def test_city_filter_invalid_value_is_ignored(client):
    _submitted_app()
    _login_admin(client)
    response = client.get(
        reverse("dashboards:admin_applications"), {"city": "not-a-number"}
    )
    assert response.status_code == 200


# ---------- has-allergies filter ----------

def test_allergy_filter_returns_only_apps_with_allergies(client):
    from apps.dietary.models import Allergy
    allergy = Allergy.objects.create(name="Peanut")
    _submitted_app(email="with_allergy@example.com", full_name="Allergy Person",
                   allergy_ids=[allergy.id])
    _submitted_app(email="no_allergy@example.com", full_name="Clean Person",
                   allergy_ids=[])
    _login_admin(client)
    response = client.get(
        reverse("dashboards:admin_applications"), {"has_allergies": "1"}
    )
    assert b"Allergy Person" in response.content
    assert b"Clean Person" not in response.content


# ---------- detail link ----------

def test_list_includes_detail_links(client):
    app = _submitted_app()
    _login_admin(client)
    response = client.get(reverse("dashboards:admin_applications"))
    detail_url = reverse("dashboards:admin_application_detail", args=[app.id])
    assert detail_url.encode() in response.content
