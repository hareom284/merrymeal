import pytest
from django.core import mail
from django.urls import reverse

from apps.accounts.models import Application

pytestmark = pytest.mark.django_db


def _diet(name="vegetarian"):
    from apps.dietary.models import DietPreference
    return DietPreference.objects.create(name=name)


def _allergy(name="peanut"):
    from apps.dietary.models import Allergy
    return Allergy.objects.create(name=name)


def _draft(**overrides):
    defaults = {
        "full_name": "Margaret",
        "email": "m@example.com",
        "dob": "1940-01-01",
        "status": Application.STATUS_DRAFT,
    }
    defaults.update(overrides)
    return Application.objects.create(**defaults)


def _start_session(client, app):
    session = client.session
    session["application_id"] = app.id
    session.save()


# ---------- form ----------

def test_dietary_form_accepts_empty_lists():
    from apps.accounts.forms import ApplicationDietaryForm
    form = ApplicationDietaryForm(data={"dietary_ids": [], "allergy_ids": []})
    assert form.is_valid(), form.errors


def test_dietary_form_parses_id_lists():
    d = _diet("vegan")
    a = _allergy("dairy")
    from apps.accounts.forms import ApplicationDietaryForm
    form = ApplicationDietaryForm(
        data={"dietary_ids": [str(d.id)], "allergy_ids": [str(a.id)]}
    )
    assert form.is_valid(), form.errors
    assert form.cleaned_data["dietary_ids"] == [d.id]
    assert form.cleaned_data["allergy_ids"] == [a.id]


# ---------- service ----------

def test_submit_application_flips_status_and_writes_ids():
    from apps.accounts.services import submit_application
    d = _diet("vegan")
    a = _allergy("dairy")
    app = _draft()

    submitted = submit_application(
        application_id=app.id,
        dietary_ids=[d.id],
        allergy_ids=[a.id],
    )

    assert submitted.status == Application.STATUS_SUBMITTED
    assert submitted.dietary_ids == [d.id]
    assert submitted.allergy_ids == [a.id]


def test_submit_application_sends_confirmation_email():
    from apps.accounts.services import submit_application
    app = _draft(email="margaret@example.com")
    submit_application(
        application_id=app.id, dietary_ids=[], allergy_ids=[]
    )
    assert len(mail.outbox) == 1
    msg = mail.outbox[0]
    assert "margaret@example.com" in msg.to
    assert "got your MerryMeal application" in msg.subject


def test_submit_application_cc_caregiver_when_applying_for_other():
    from apps.accounts.services import submit_application
    app = _draft(
        email="margaret@example.com",
        applying_for_other=True,
        caregiver_full_name="Jane",
        caregiver_email="jane@example.com",
    )
    submit_application(application_id=app.id, dietary_ids=[], allergy_ids=[])
    msg = mail.outbox[0]
    assert "jane@example.com" in (msg.cc or [])


def test_submit_application_rejects_non_draft():
    from apps.accounts.services import submit_application
    app = _draft()
    app.status = Application.STATUS_SUBMITTED
    app.save()
    with pytest.raises(ValueError, match="draft"):
        submit_application(application_id=app.id, dietary_ids=[], allergy_ids=[])


def test_submit_application_rejects_unknown_diet_id():
    from apps.accounts.services import submit_application
    app = _draft()
    with pytest.raises(ValueError, match="diet"):
        submit_application(application_id=app.id, dietary_ids=[99999], allergy_ids=[])


# ---------- view ----------

def test_step_3_redirects_to_step_1_without_session(client):
    response = client.get(reverse("accounts:application_step_3"))
    assert response.status_code == 302
    assert response.url.endswith("/apply/")


def test_step_3_get_renders(client):
    _diet("vegan")
    _allergy("dairy")
    app = _draft()
    _start_session(client, app)
    response = client.get(reverse("accounts:application_step_3"))
    assert response.status_code == 200
    assert b"Step 3 of 3" in response.content
    assert b"vegan" in response.content
    assert b"dairy" in response.content


def test_step_3_post_submits_clears_session_and_redirects(client):
    d = _diet("vegan")
    app = _draft()
    _start_session(client, app)

    response = client.post(
        reverse("accounts:application_step_3"),
        {"dietary_ids": [d.id], "allergy_ids": []},
    )
    assert response.status_code == 302
    assert response.url.endswith("/apply/done/")
    app.refresh_from_db()
    assert app.status == Application.STATUS_SUBMITTED
    assert app.dietary_ids == [d.id]
    assert "application_id" not in client.session
    assert len(mail.outbox) == 1


def test_done_page_renders(client):
    response = client.get(reverse("accounts:application_done"))
    assert response.status_code == 200
    assert b"3" in response.content
    assert b"business days" in response.content
