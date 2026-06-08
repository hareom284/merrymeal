import pytest
from django.urls import reverse

from apps.accounts.tests.factories import UserFactory


pytestmark = pytest.mark.django_db


# ---------- form ----------

def test_contact_form_requires_full_name_email_dob():
    from apps.accounts.forms import ApplicationContactForm
    form = ApplicationContactForm(data={})
    assert not form.is_valid()
    assert {"full_name", "email", "dob"} <= set(form.errors)


def test_contact_form_rejects_bad_email():
    from apps.accounts.forms import ApplicationContactForm
    form = ApplicationContactForm(
        data={"full_name": "M", "email": "not-an-email", "dob": "1940-01-01"}
    )
    assert not form.is_valid()
    assert "email" in form.errors


def test_contact_form_rejects_email_that_collides_with_existing_user():
    UserFactory(email="taken@example.com")
    from apps.accounts.forms import ApplicationContactForm
    form = ApplicationContactForm(
        data={
            "full_name": "M",
            "email": "taken@example.com",
            "dob": "1940-01-01",
        }
    )
    assert not form.is_valid()
    assert "email" in form.errors


# ---------- service ----------

def test_create_draft_application_persists_a_draft_row():
    from apps.accounts.services import create_draft_application
    from apps.accounts.models import Application

    app = create_draft_application(
        full_name="Margaret W.",
        email="margaret@example.com",
        dob="1940-01-01",
        phone="0400000000",
    )

    assert isinstance(app, Application)
    assert app.id is not None
    assert app.status == "draft"
    assert app.full_name == "Margaret W."
    assert app.applying_for_other is False


def test_create_draft_application_rejects_existing_user_email():
    UserFactory(email="taken@example.com")
    from apps.accounts.services import create_draft_application
    with pytest.raises(ValueError, match="already exists"):
        create_draft_application(
            full_name="M",
            email="taken@example.com",
            dob="1940-01-01",
        )


# ---------- view ----------

def test_get_apply_renders_step_1(client):
    response = client.get(reverse("accounts:application_step_1"))
    assert response.status_code == 200
    assert b"Step 1 of 3" in response.content
    assert b'name="full_name"' in response.content


def test_post_apply_creates_draft_and_redirects_to_step_2(client):
    response = client.post(
        reverse("accounts:application_step_1"),
        {
            "full_name": "Margaret W.",
            "email": "margaret@example.com",
            "dob": "1940-01-01",
            "phone": "0400000000",
        },
    )
    assert response.status_code == 302
    assert response.url.endswith("/apply/address/")

    from apps.accounts.models import Application
    app = Application.objects.get(email="margaret@example.com")
    assert app.status == "draft"
    assert client.session["application_id"] == app.id


def test_post_apply_renders_errors_when_invalid(client):
    response = client.post(reverse("accounts:application_step_1"), {})
    assert response.status_code == 200
    assert b"This field is required" in response.content
