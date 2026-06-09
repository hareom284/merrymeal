"""Tests for the admin profile page (Story 12.10)."""
import pytest

from apps.accounts.tests.factories import UserFactory


@pytest.mark.django_db
def test_admin_profile_requires_admin(client):
    user = UserFactory(role="member")
    client.force_login(user)
    response = client.get("/admin/profile/")
    assert response.status_code == 403


@pytest.mark.django_db
def test_admin_profile_renders_for_admin(client):
    admin = UserFactory(role="admin", full_name="Alex Admin")
    client.force_login(admin)
    response = client.get("/admin/profile/")
    assert response.status_code == 200
    body = response.content
    assert b"Alex Admin" in body
    assert b"Admin" in body  # role badge


@pytest.mark.django_db
def test_admin_profile_has_sign_out_form(client):
    admin = UserFactory(role="admin")
    client.force_login(admin)
    response = client.get("/admin/profile/")
    body = response.content
    assert b"Sign out" in body
    assert b'action="/accounts/logout/"' in body


@pytest.mark.django_db
def test_admin_nav_includes_profile_tab(client):
    """Admin bottom nav grows to 5 tabs: Home / Applications / Kitchens
    / Audit / Profile."""
    admin = UserFactory(role="admin")
    client.force_login(admin)
    response = client.get("/admin/home/")
    body = response.content
    assert b"/admin/profile/" in body
