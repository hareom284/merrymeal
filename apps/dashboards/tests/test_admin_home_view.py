"""Story 6.1 — admin home view + HTMX partial endpoint."""
import pytest
from django.urls import reverse

from apps.accounts.tests.factories import UserFactory


@pytest.mark.django_db
def test_admin_can_load_home(client):
    admin = UserFactory(email="admin@mm.com", role="admin")
    client.force_login(admin)

    response = client.get(reverse("dashboards:admin_home"))
    assert response.status_code == 200
    assert b"Pending applications" in response.content
    assert b"Expiring stock" in response.content
    assert b"Failed deliveries today" in response.content
    assert b"Unassigned deliveries today" in response.content
    assert b"Recent food-safety failures" in response.content


@pytest.mark.django_db
def test_non_admin_forbidden(client):
    member = UserFactory(email="member@mm.com", role="member")
    client.force_login(member)

    response = client.get(reverse("dashboards:admin_home"))
    # @role_required redirects unauthenticated users; logged-in non-admins
    # get a 403.
    assert response.status_code == 403


@pytest.mark.django_db
def test_anonymous_user_redirected(client):
    response = client.get(reverse("dashboards:admin_home"))
    assert response.status_code in (302, 403)


@pytest.mark.django_db
def test_cards_partial_returns_only_card_html(client):
    admin = UserFactory(email="admin2@mm.com", role="admin")
    client.force_login(admin)

    response = client.get(reverse("dashboards:admin_home_cards"))
    assert response.status_code == 200
    # The partial must NOT include the navigation chrome or <html> wrapper.
    assert b"<html" not in response.content
    assert b"<nav" not in response.content
    # But MUST include card content.
    assert b"Pending applications" in response.content


@pytest.mark.django_db
def test_cards_partial_non_admin_forbidden(client):
    member = UserFactory(email="member3@mm.com", role="member")
    client.force_login(member)

    response = client.get(reverse("dashboards:admin_home_cards"))
    assert response.status_code == 403


@pytest.mark.django_db
def test_home_uses_htmx_refresh(client):
    admin = UserFactory(email="admin3@mm.com", role="admin")
    client.force_login(admin)

    response = client.get(reverse("dashboards:admin_home"))
    assert response.status_code == 200
    # HTMX 5-minute cadence wired on the grid container.
    assert b'hx-trigger="every 300s"' in response.content
    assert b"admin/home/cards/" in response.content
