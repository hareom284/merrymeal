"""Public partner-org signup form.

Charities, clinicians and other organisations register their org via
``/apply-partner/``. The submission lands as an ``Application`` row
with ``metadata["kind"] == "partner_signup"`` so admins triage it
through the existing application inbox; on approval an admin manually
creates the ``Partner`` row via the existing
``dashboards:admin_partner_create`` page.

The Partner table schema is locked (legal_name + type only — no
status / contact_email columns), so we cannot persist a pending
``Partner`` row directly. Routing through ``Application.metadata``
keeps the public path schema-respecting.
"""
import pytest
from django.urls import reverse

from apps.accounts.models import Application

URL_FORM = "partner_signup_form"
URL_THANKS = "partner_signup_thanks"


def _valid_payload(**overrides):
    payload = {
        "org_legal_name": "Helping Hands Inc.",
        "org_type": "charity",
        "contact_name": "Jane Carer",
        "contact_email": "jane@helpinghands.org",
        "contact_phone": "0400 000 000",
        "message": "We work with elderly clients in Coburg.",
    }
    payload.update(overrides)
    return payload


@pytest.mark.django_db
def test_anonymous_can_get_form(client):
    resp = client.get(reverse(URL_FORM))
    assert resp.status_code == 200
    assert b"Partner with us" in resp.content or b"partner" in resp.content.lower()


@pytest.mark.django_db
def test_post_creates_submitted_application_with_metadata(client):
    resp = client.post(reverse(URL_FORM), _valid_payload())
    assert resp.status_code == 302

    app = Application.objects.order_by("-id").first()
    assert app is not None
    assert app.status == Application.STATUS_SUBMITTED
    assert app.full_name == "Jane Carer"
    assert app.email == "jane@helpinghands.org"
    assert app.metadata["kind"] == "partner_signup"
    assert app.metadata["org_legal_name"] == "Helping Hands Inc."
    assert app.metadata["org_type"] == "charity"
    assert app.metadata["contact_phone"] == "0400 000 000"
    assert "Coburg" in app.metadata["message"]


@pytest.mark.django_db
def test_post_redirects_to_thanks(client):
    resp = client.post(reverse(URL_FORM), _valid_payload())
    assert resp.status_code == 302
    assert reverse(URL_THANKS) in resp.url


@pytest.mark.django_db
def test_post_with_missing_org_name_fails(client):
    resp = client.post(reverse(URL_FORM), _valid_payload(org_legal_name=""))
    assert resp.status_code == 200
    assert Application.objects.count() == 0
    body = resp.content.decode().lower()
    assert "required" in body or "this field" in body


@pytest.mark.django_db
def test_post_with_invalid_org_type_fails(client):
    resp = client.post(reverse(URL_FORM), _valid_payload(org_type="not-a-type"))
    assert resp.status_code == 200
    assert Application.objects.count() == 0


@pytest.mark.django_db
def test_post_with_missing_contact_email_fails(client):
    resp = client.post(reverse(URL_FORM), _valid_payload(contact_email=""))
    assert resp.status_code == 200
    assert Application.objects.count() == 0


@pytest.mark.django_db
def test_post_with_blank_optional_fields_succeeds(client):
    resp = client.post(
        reverse(URL_FORM),
        _valid_payload(contact_phone="", message=""),
    )
    assert resp.status_code == 302

    app = Application.objects.order_by("-id").first()
    assert app.metadata["contact_phone"] == ""
    assert app.metadata["message"] == ""


@pytest.mark.django_db
def test_thanks_page_renders(client):
    resp = client.get(reverse(URL_THANKS))
    assert resp.status_code == 200
    assert b"thank" in resp.content.lower() or b"received" in resp.content.lower()


@pytest.mark.django_db
def test_duplicate_submissions_are_allowed(client):
    """One person may register multiple orgs (or re-submit if the first
    was missed). Each submission lands as its own ``Application`` row."""
    client.post(reverse(URL_FORM), _valid_payload())
    client.post(
        reverse(URL_FORM),
        _valid_payload(org_legal_name="Helping Hands East"),
    )
    assert Application.objects.count() == 2


@pytest.mark.django_db
def test_landing_links_to_apply_partner(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert reverse(URL_FORM).encode() in resp.content
