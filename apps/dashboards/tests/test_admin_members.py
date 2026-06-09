"""Tests for the admin members directory + deactivate/reactivate flows
(Story 12.11)."""
import pytest

from apps.accounts.tests.factories import UserFactory


@pytest.mark.django_db
def test_members_list_requires_admin(client):
    user = UserFactory(role="member")
    client.force_login(user)
    response = client.get("/admin/members/")
    assert response.status_code == 403


@pytest.mark.django_db
def test_members_list_lists_only_members(client):
    """The directory shows ``role=member`` only — admins, volunteers,
    donors etc. don't leak in. They each have their own UI eventually."""
    admin = UserFactory(role="admin")
    m1 = UserFactory(role="member", full_name="Alice Member", email="alice@example.com")
    m2 = UserFactory(role="member", full_name="Bob Member", email="bob@example.com")
    UserFactory(role="volunteer", full_name="Vera Vol", email="vera@example.com")
    UserFactory(role="donor", full_name="Dan Donor", email="dan@example.com")

    client.force_login(admin)
    response = client.get("/admin/members/")
    body = response.content
    assert response.status_code == 200
    assert b"Alice Member" in body
    assert b"Bob Member" in body
    assert b"Vera Vol" not in body
    assert b"Dan Donor" not in body
    # The detail link is the navigable path; check it exists per member.
    assert f"/admin/members/{m1.id}/".encode() in body
    assert f"/admin/members/{m2.id}/".encode() in body


@pytest.mark.django_db
def test_members_list_search_by_name(client):
    admin = UserFactory(role="admin")
    UserFactory(role="member", full_name="Margaret Chen", email="m@example.com")
    UserFactory(role="member", full_name="Bob Smith", email="b@example.com")
    client.force_login(admin)

    response = client.get("/admin/members/", {"q": "Margaret"})
    body = response.content
    assert b"Margaret Chen" in body
    assert b"Bob Smith" not in body


@pytest.mark.django_db
def test_members_list_filter_inactive(client):
    admin = UserFactory(role="admin")
    UserFactory(role="member", full_name="Alice A", email="a@a.com", is_active=True)
    UserFactory(role="member", full_name="Inactive I", email="i@i.com", is_active=False)
    client.force_login(admin)

    response = client.get("/admin/members/", {"status": "inactive"})
    body = response.content
    assert b"Inactive I" in body
    assert b"Alice A" not in body


@pytest.mark.django_db
def test_member_detail_renders(client):
    admin = UserFactory(role="admin")
    member = UserFactory(role="member", full_name="Margaret Chen")
    client.force_login(admin)
    response = client.get(f"/admin/members/{member.id}/")
    assert response.status_code == 200
    assert b"Margaret Chen" in response.content


@pytest.mark.django_db
def test_member_detail_404_for_non_member(client):
    """Looking up a non-member by ID via /admin/members/<pk>/ must
    404 — admins land on the right CRUD for the right role."""
    admin = UserFactory(role="admin")
    volunteer = UserFactory(role="volunteer")
    client.force_login(admin)
    response = client.get(f"/admin/members/{volunteer.id}/")
    assert response.status_code == 404


@pytest.mark.django_db
def test_deactivate_flips_is_active_and_redirects(client):
    admin = UserFactory(role="admin")
    member = UserFactory(role="member", is_active=True)
    client.force_login(admin)

    response = client.post(f"/admin/members/{member.id}/deactivate/")
    assert response.status_code == 302
    assert response.url == f"/admin/members/{member.id}/"

    member.refresh_from_db()
    assert member.is_active is False


@pytest.mark.django_db
def test_reactivate_flips_is_active_back(client):
    admin = UserFactory(role="admin")
    member = UserFactory(role="member", is_active=False)
    client.force_login(admin)

    response = client.post(f"/admin/members/{member.id}/reactivate/")
    assert response.status_code == 302

    member.refresh_from_db()
    assert member.is_active is True


@pytest.mark.django_db
def test_deactivate_is_idempotent(client):
    """Calling deactivate twice mustn't error — the service is a no-op
    on an already-inactive member."""
    admin = UserFactory(role="admin")
    member = UserFactory(role="member", is_active=False)
    client.force_login(admin)
    response = client.post(f"/admin/members/{member.id}/deactivate/")
    assert response.status_code == 302
    member.refresh_from_db()
    assert member.is_active is False


@pytest.mark.django_db
def test_deactivate_requires_post(client):
    admin = UserFactory(role="admin")
    member = UserFactory(role="member")
    client.force_login(admin)
    response = client.get(f"/admin/members/{member.id}/deactivate/")
    assert response.status_code == 405


@pytest.mark.django_db
def test_admin_home_links_to_members_directory(client):
    """Story 12.11 — admins reach members via a card on /admin/home/
    (since the bottom nav stays at 5 tabs)."""
    admin = UserFactory(role="admin")
    client.force_login(admin)
    response = client.get("/admin/home/")
    assert b"/admin/members/" in response.content
