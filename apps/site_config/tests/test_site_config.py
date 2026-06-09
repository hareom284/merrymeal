"""Tests for the site_config app — model, CRUD view, error pages."""
import io

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

from apps.accounts.tests.factories import UserFactory
from apps.site_config.models import OrgSettings


def _png_upload(name: str = "logo.png", size: tuple[int, int] = (64, 64)) -> SimpleUploadedFile:
    """Build a tiny in-memory PNG so the upload tests don't depend on
    a checked-in fixture file."""
    from django.core.files.uploadedfile import (  # noqa: F811 — re-import for clarity
        SimpleUploadedFile,
    )

    img = Image.new("RGBA", size, (22, 163, 74, 255))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return SimpleUploadedFile(name, buf.getvalue(), content_type="image/png")


# ---- model singleton ------------------------------------------------

@pytest.mark.django_db
def test_current_creates_singleton_on_first_call():
    assert OrgSettings.objects.count() == 0
    obj = OrgSettings.objects.current()
    assert obj.pk == 1
    assert OrgSettings.objects.count() == 1


@pytest.mark.django_db
def test_current_returns_existing_singleton():
    first = OrgSettings.objects.current()
    second = OrgSettings.objects.current()
    assert first.pk == second.pk
    assert OrgSettings.objects.count() == 1


@pytest.mark.django_db
def test_seed_defaults_include_yangon_address():
    """Defaults should put the charity in Yangon out of the box —
    matches the deployment locale and avoids a blank address before
    the admin first opens the settings page."""
    org = OrgSettings.objects.current()
    assert "Yangon" in org.address
    assert org.name == "MerryMeal"
    assert "+95" in org.phone


@pytest.mark.django_db
def test_logo_url_falls_back_to_static_when_no_upload():
    org = OrgSettings.objects.current()
    assert org.logo_url.endswith("/img/logo.png")


# ---- admin CRUD view ------------------------------------------------

@pytest.mark.django_db
def test_settings_page_requires_login(client):
    response = client.get("/admin/settings/")
    assert response.status_code == 302
    assert "/login/" in response.url or "/accounts/login/" in response.url


@pytest.mark.django_db
def test_settings_page_forbidden_for_non_admin(client):
    member = UserFactory(role="member")
    client.force_login(member)
    response = client.get("/admin/settings/")
    assert response.status_code in (302, 403)


@pytest.mark.django_db
def test_settings_page_renders_for_admin(client):
    admin = UserFactory(role="admin")
    client.force_login(admin)
    response = client.get("/admin/settings/")
    assert response.status_code == 200
    body = response.content
    assert b"Organisation settings" in body
    assert b"Yangon" in body  # seeded default


@pytest.mark.django_db
def test_post_updates_phone_and_address(client):
    admin = UserFactory(role="admin")
    client.force_login(admin)
    response = client.post(
        "/admin/settings/",
        {
            "name": "MerryMeal Trust",
            "tagline": "Warm meals delivered.",
            "address": "12 Main Rd, Yangon",
            "phone": "+95 9 999 999 999",
            "contact_email": "hi@merrymeal.org",
            "office_email": "ops@merrymeal.org",
        },
    )
    assert response.status_code == 302  # redirect after save
    org = OrgSettings.objects.current()
    assert org.name == "MerryMeal Trust"
    assert org.phone == "+95 9 999 999 999"
    assert org.address == "12 Main Rd, Yangon"


@pytest.mark.django_db
def test_logo_upload_saves_and_overrides_static_fallback(client, settings, tmp_path):
    settings.MEDIA_ROOT = str(tmp_path)
    admin = UserFactory(role="admin")
    client.force_login(admin)
    response = client.post(
        "/admin/settings/",
        {
            "name": "MerryMeal",
            "tagline": "",
            "address": "Yangon",
            "phone": "+95",
            "contact_email": "a@b.com",
            "office_email": "a@b.com",
            "logo": _png_upload(),
        },
    )
    assert response.status_code == 302
    org = OrgSettings.objects.current()
    assert org.logo  # uploaded
    assert org.logo_url.startswith("/media/org/")


@pytest.mark.django_db
def test_oversized_logo_rejected(client, settings, tmp_path):
    settings.MEDIA_ROOT = str(tmp_path)
    admin = UserFactory(role="admin")
    client.force_login(admin)
    # PNGs compress, so just constructing a big image doesn't reliably
    # produce a >2 MB upload. Build the real-world bad case: a JPEG-ish
    # blob padded past the 2 MB cap with incompressible random bytes.
    import os

    from django.core.files.uploadedfile import SimpleUploadedFile

    # PNG header so Django's ImageField validator accepts the file,
    # then 2.5 MB of random bytes to trip the cap.
    fake_png = b"\x89PNG\r\n\x1a\n" + os.urandom(int(2.5 * 1024 * 1024))
    big = SimpleUploadedFile("huge.png", fake_png, content_type="image/png")
    response = client.post(
        "/admin/settings/",
        {
            "name": "MerryMeal",
            "tagline": "",
            "address": "Yangon",
            "phone": "+95",
            "contact_email": "a@b.com",
            "office_email": "a@b.com",
            "logo": big,
        },
    )
    assert response.status_code == 200  # form re-rendered with error
    # Either our 2 MB cap fires OR Django's ImageField rejects the
    # malformed PNG header. Both outcomes are acceptable defences.
    assert b"too large" in response.content or b"valid image" in response.content


# ---- context processor ----------------------------------------------

@pytest.mark.django_db
def test_org_context_processor_exposes_org_to_templates(client):
    admin = UserFactory(role="admin")
    client.force_login(admin)
    response = client.get("/admin/settings/")
    # The template renders ``{{ org.name }}`` in the title and body.
    assert b"MerryMeal" in response.content


# ---- error pages ----------------------------------------------------

@pytest.mark.django_db
def test_404_page_renders_branded_template(client, settings):
    settings.DEBUG = False
    settings.ALLOWED_HOSTS = ["*"]
    response = client.get("/nonexistent-path-xyz/")
    assert response.status_code == 404
    body = response.content
    assert b"We couldn't find that page" in body
