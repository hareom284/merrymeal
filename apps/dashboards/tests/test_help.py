"""Tests for the member-facing Help & contact page (Story 12.3)."""
import pytest

from apps.accounts.tests.factories import UserFactory


@pytest.mark.django_db
def test_help_page_requires_login(client):
    """Anonymous visitors get bounced to login — Help reveals support
    contacts (phone, email) that exist on the staff side, so login-gated."""
    response = client.get("/help/")
    assert response.status_code == 302
    assert "/login/" in response.url or "/accounts/login/" in response.url


@pytest.mark.django_db
def test_help_page_renders_for_authenticated_member(client):
    user = UserFactory(role="member")
    client.force_login(user)
    response = client.get("/help/")
    assert response.status_code == 200


@pytest.mark.django_db
def test_help_page_shows_call_cta(client):
    """The top-of-page \"Call MerryMeal\" CTA must be a real tel: link so
    a senior on a phone can one-tap dial — not a placeholder."""
    user = UserFactory(role="member")
    client.force_login(user)
    response = client.get("/help/")
    body = response.content
    assert b"Call MerryMeal" in body
    assert b'href="tel:' in body


@pytest.mark.django_db
def test_help_page_lists_quick_actions(client):
    user = UserFactory(role="member")
    client.force_login(user)
    response = client.get("/help/")
    body = response.content
    assert b"Pause" in body
    assert b"Change delivery" in body
    assert b"dietary" in body.lower()


@pytest.mark.django_db
def test_help_page_lists_faqs(client):
    user = UserFactory(role="member")
    client.force_login(user)
    response = client.get("/help/")
    body = response.content
    assert b"What time" in body
    assert b"allergy" in body.lower()
    assert b"share my meal" in body.lower()


@pytest.mark.django_db
def test_help_page_has_no_dead_links(client):
    """Quick-action and CTA links must resolve. ``href="#"`` placeholders
    would silently dead-end the user; the page is supposed to *help*."""
    user = UserFactory(role="member")
    client.force_login(user)
    response = client.get("/help/")
    assert b'href="#"' not in response.content
