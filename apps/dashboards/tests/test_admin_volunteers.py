"""Tests for the admin volunteers directory + deactivate/reactivate
(Story 12.13)."""
import pytest

from apps.accounts.tests.factories import UserFactory
from apps.volunteers.models import Availability


@pytest.mark.django_db
def test_volunteers_list_requires_admin(client):
    user = UserFactory(role="member")
    client.force_login(user)
    response = client.get("/admin/volunteers/")
    assert response.status_code == 403


@pytest.mark.django_db
def test_volunteers_list_lists_only_volunteers(client):
    """The directory shows ``role=volunteer`` only. Members, admins,
    donors etc. each have their own (or future) CRUDs and must not
    leak into the volunteer list."""
    admin = UserFactory(role="admin")
    v1 = UserFactory(role="volunteer", full_name="Vera Vol", email="v@a.com")
    UserFactory(role="member", full_name="Margaret Member", email="m@a.com")
    UserFactory(role="donor", full_name="Dan Donor", email="d@a.com")

    client.force_login(admin)
    response = client.get("/admin/volunteers/")
    body = response.content
    assert response.status_code == 200
    assert b"Vera Vol" in body
    assert b"Margaret Member" not in body
    assert b"Dan Donor" not in body
    assert f"/admin/volunteers/{v1.id}/".encode() in body


@pytest.mark.django_db
def test_volunteers_list_search_by_name(client):
    admin = UserFactory(role="admin")
    UserFactory(role="volunteer", full_name="Alice Volunteer", email="a@a.com")
    UserFactory(role="volunteer", full_name="Bob Volunteer", email="b@a.com")
    client.force_login(admin)
    response = client.get("/admin/volunteers/", {"q": "Alice"})
    body = response.content
    assert b"Alice Volunteer" in body
    assert b"Bob Volunteer" not in body


@pytest.mark.django_db
def test_volunteer_detail_renders_with_availability_grid(client):
    admin = UserFactory(role="admin")
    v = UserFactory(role="volunteer", full_name="Vera Vol")
    Availability.objects.create(volunteer=v, day_of_week="mon", day_phrase="morning")
    Availability.objects.create(volunteer=v, day_of_week="fri", day_phrase="afternoon")
    client.force_login(admin)
    response = client.get(f"/admin/volunteers/{v.id}/")
    assert response.status_code == 200
    body = response.content
    # The grid is rendered as a table; assert the headers appear and
    # that the volunteer's name renders.
    assert b"Vera Vol" in body
    assert b"morning" in body.lower() or b"Morning" in body
    assert b"afternoon" in body.lower() or b"Afternoon" in body


@pytest.mark.django_db
def test_volunteer_detail_404_for_non_volunteer(client):
    admin = UserFactory(role="admin")
    member = UserFactory(role="member")
    client.force_login(admin)
    response = client.get(f"/admin/volunteers/{member.id}/")
    assert response.status_code == 404


@pytest.mark.django_db
def test_deactivate_volunteer(client):
    admin = UserFactory(role="admin")
    v = UserFactory(role="volunteer", is_active=True)
    client.force_login(admin)
    response = client.post(f"/admin/volunteers/{v.id}/deactivate/")
    assert response.status_code == 302
    v.refresh_from_db()
    assert v.is_active is False


@pytest.mark.django_db
def test_reactivate_volunteer(client):
    admin = UserFactory(role="admin")
    v = UserFactory(role="volunteer", is_active=False)
    client.force_login(admin)
    response = client.post(f"/admin/volunteers/{v.id}/reactivate/")
    assert response.status_code == 302
    v.refresh_from_db()
    assert v.is_active is True


@pytest.mark.django_db
def test_admin_home_links_to_volunteers(client):
    admin = UserFactory(role="admin")
    client.force_login(admin)
    response = client.get("/admin/home/")
    assert b"/admin/volunteers/" in response.content
