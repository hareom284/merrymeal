import pytest
from django.urls import reverse

from apps.accounts.models import Application


pytestmark = pytest.mark.django_db


def _make_city(name="Melbourne"):
    from apps.accounts.models import City
    return City.objects.create(name=name)


def _make_draft(email="m@example.com"):
    return Application.objects.create(
        full_name="Margaret",
        email=email,
        dob="1940-01-01",
        status=Application.STATUS_DRAFT,
    )


def _start_session(client, app):
    session = client.session
    session["application_id"] = app.id
    session.save()


# ---------- form ----------

def test_address_form_requires_street_postcode_city():
    from apps.accounts.forms import ApplicationAddressForm
    form = ApplicationAddressForm(data={})
    assert not form.is_valid()
    assert {"street", "postal_code", "city"} <= set(form.errors)


def test_address_form_default_label_is_home():
    from apps.accounts.forms import ApplicationAddressForm
    form = ApplicationAddressForm()
    assert form.fields["label"].initial == "Home"


# ---------- service ----------

def test_update_application_address_persists_fields():
    from apps.accounts.services import update_application_address
    city = _make_city()
    app = _make_draft()

    updated = update_application_address(
        application=app,
        label="Home",
        street="12 Main St",
        postal_code="3000",
        city=city,
    )

    assert updated.id == app.id
    assert updated.street == "12 Main St"
    assert updated.postal_code == "3000"
    assert updated.city_id == city.id
    assert updated.address_label == "Home"


def test_update_application_address_refuses_non_draft():
    from apps.accounts.services import update_application_address
    city = _make_city()
    app = _make_draft()
    app.status = Application.STATUS_SUBMITTED
    app.save()
    with pytest.raises(ValueError, match="draft"):
        update_application_address(
            application=app,
            label="Home",
            street="12 Main St",
            postal_code="3000",
            city=city,
        )


# ---------- view ----------

def test_step_2_redirects_to_step_1_without_session_token(client):
    response = client.get(reverse("accounts:application_step_2"))
    assert response.status_code == 302
    assert response.url.endswith("/apply/")


def test_step_2_get_renders_with_session_token(client):
    app = _make_draft()
    _start_session(client, app)
    response = client.get(reverse("accounts:application_step_2"))
    assert response.status_code == 200
    assert b"Step 2 of 3" in response.content
    assert b'name="street"' in response.content


def test_step_2_post_updates_application_and_redirects(client):
    city = _make_city()
    app = _make_draft()
    _start_session(client, app)

    response = client.post(
        reverse("accounts:application_step_2"),
        {
            "label": "Home",
            "street": "12 Main St",
            "postal_code": "3000",
            "city": city.id,
        },
    )
    assert response.status_code == 302
    assert response.url.endswith("/apply/dietary/")

    app.refresh_from_db()
    assert app.street == "12 Main St"
    assert app.city_id == city.id
    assert app.status == Application.STATUS_DRAFT


def test_step_2_renders_errors_when_invalid(client):
    app = _make_draft()
    _start_session(client, app)
    response = client.post(reverse("accounts:application_step_2"), {})
    assert response.status_code == 200
    assert b"This field is required" in response.content


def test_step_2_clears_stale_session_for_submitted_application(client):
    app = _make_draft()
    app.status = Application.STATUS_SUBMITTED
    app.save()
    _start_session(client, app)
    response = client.get(reverse("accounts:application_step_2"))
    assert response.status_code == 302
    assert response.url.endswith("/apply/")
    assert "application_id" not in client.session
