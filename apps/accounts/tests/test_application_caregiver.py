import pytest
from django.urls import reverse

from apps.accounts.models import Application
from apps.accounts.tests.factories import UserFactory


pytestmark = pytest.mark.django_db


# ---------- form ----------

def test_form_without_toggle_ignores_caregiver_fields():
    from apps.accounts.forms import ApplicationContactForm
    form = ApplicationContactForm(
        data={
            "full_name": "Margaret W.",
            "email": "margaret@example.com",
            "dob": "1940-01-01",
            "applying_for_other": "",
        }
    )
    assert form.is_valid(), form.errors
    assert form.cleaned_data["applying_for_other"] is False
    assert form.cleaned_data.get("caregiver_full_name") in (None, "")


def test_form_with_toggle_requires_caregiver_fields():
    from apps.accounts.forms import ApplicationContactForm
    form = ApplicationContactForm(
        data={
            "full_name": "Margaret W.",
            "email": "margaret@example.com",
            "dob": "1940-01-01",
            "applying_for_other": "on",
        }
    )
    assert not form.is_valid()
    assert {"caregiver_full_name", "caregiver_email", "relationship"} <= set(
        form.errors
    )


def test_form_with_toggle_and_full_caregiver_data_validates():
    from apps.accounts.forms import ApplicationContactForm
    form = ApplicationContactForm(
        data={
            "full_name": "Margaret W.",
            "email": "margaret@example.com",
            "dob": "1940-01-01",
            "applying_for_other": "on",
            "caregiver_full_name": "Jane W.",
            "caregiver_email": "jane@example.com",
            "caregiver_phone": "0411111111",
            "relationship": "family",
        }
    )
    assert form.is_valid(), form.errors
    assert form.cleaned_data["applying_for_other"] is True
    assert form.cleaned_data["caregiver_email"] == "jane@example.com"


def test_form_rejects_member_email_collision_even_when_for_other():
    UserFactory(email="margaret@example.com")
    from apps.accounts.forms import ApplicationContactForm
    form = ApplicationContactForm(
        data={
            "full_name": "Margaret W.",
            "email": "margaret@example.com",
            "dob": "1940-01-01",
            "applying_for_other": "on",
            "caregiver_full_name": "Jane W.",
            "caregiver_email": "jane@example.com",
            "relationship": "family",
        }
    )
    assert not form.is_valid()
    assert "email" in form.errors


def test_form_accepts_existing_caregiver_email_and_flags_it():
    UserFactory(email="jane@example.com", role="caregiver")
    from apps.accounts.forms import ApplicationContactForm
    form = ApplicationContactForm(
        data={
            "full_name": "Margaret W.",
            "email": "margaret@example.com",
            "dob": "1940-01-01",
            "applying_for_other": "on",
            "caregiver_full_name": "Jane W.",
            "caregiver_email": "jane@example.com",
            "relationship": "family",
        }
    )
    assert form.is_valid(), form.errors
    assert form.cleaned_data["existing_caregiver"] is True


# ---------- service ----------

def test_create_draft_application_persists_caregiver_columns():
    from apps.accounts.services import create_draft_application
    app = create_draft_application(
        full_name="Margaret W.",
        email="margaret@example.com",
        dob="1940-01-01",
        applying_for_other=True,
        caregiver_full_name="Jane W.",
        caregiver_email="JANE@Example.com",
        caregiver_phone="0411111111",
        relationship="family",
    )
    assert app.applying_for_other is True
    assert app.caregiver_full_name == "Jane W."
    assert app.caregiver_email == "jane@example.com"
    assert app.caregiver_phone == "0411111111"
    assert app.relationship == "family"


def test_create_draft_application_keeps_caregiver_columns_null_when_off():
    from apps.accounts.services import create_draft_application
    app = create_draft_application(
        full_name="Margaret W.",
        email="margaret@example.com",
        dob="1940-01-01",
    )
    assert app.applying_for_other is False
    assert app.caregiver_full_name is None
    assert app.caregiver_email is None
    assert app.relationship is None


# ---------- view ----------

def test_post_step_1_for_other_sets_session_flags(client):
    response = client.post(
        reverse("accounts:application_step_1"),
        {
            "full_name": "Margaret W.",
            "email": "margaret@example.com",
            "dob": "1940-01-01",
            "applying_for_other": "on",
            "caregiver_full_name": "Jane W.",
            "caregiver_email": "jane@example.com",
            "relationship": "family",
        },
    )
    assert response.status_code == 302
    assert response.url.endswith("/apply/address/")

    app = Application.objects.get(email="margaret@example.com")
    assert app.applying_for_other is True
    assert app.caregiver_email == "jane@example.com"

    assert client.session["application_id"] == app.id
    assert client.session.get("existing_caregiver") in (False, None)


def test_post_step_1_existing_caregiver_email_flags_session(client):
    UserFactory(email="jane@example.com", role="caregiver")
    response = client.post(
        reverse("accounts:application_step_1"),
        {
            "full_name": "Margaret W.",
            "email": "margaret@example.com",
            "dob": "1940-01-01",
            "applying_for_other": "on",
            "caregiver_full_name": "Jane W.",
            "caregiver_email": "jane@example.com",
            "relationship": "family",
        },
    )
    assert response.status_code == 302
    assert client.session.get("existing_caregiver") is True


def test_get_step_1_renders_caregiver_toggle(client):
    response = client.get(reverse("accounts:application_step_1"))
    assert response.status_code == 200
    assert b"applying_for_other" in response.content
    assert b"someone else" in response.content
