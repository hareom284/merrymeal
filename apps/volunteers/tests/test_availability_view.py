import pytest
from django.urls import reverse

from apps.accounts.tests.factories import UserFactory
from apps.volunteers.models import Availability
from apps.volunteers.tests.factories import VolunteerFactory


@pytest.mark.django_db
def test_get_renders_grid_with_21_cells(client):
    vol = VolunteerFactory()
    client.force_login(vol)
    resp = client.get(reverse("volunteers:availability"))
    assert resp.status_code == 200
    # 7 days × 3 phrases = 21 cell buttons.
    assert resp.content.count(b'data-cell="slot"') == 21


@pytest.mark.django_db
def test_anonymous_redirects_to_login(client):
    resp = client.get(reverse("volunteers:availability"))
    assert resp.status_code == 302
    assert "/login" in resp.url or "accounts/login" in resp.url


@pytest.mark.django_db
def test_member_role_gets_403(client):
    member = UserFactory(role="member")
    client.force_login(member)
    resp = client.get(reverse("volunteers:availability"))
    assert resp.status_code == 403


@pytest.mark.django_db
def test_htmx_toggle_creates_then_marks_pressed(client):
    vol = VolunteerFactory()
    client.force_login(vol)
    resp = client.post(
        reverse("volunteers:availability_toggle"),
        data={"day": "mon", "phrase": "morning"},
        HTTP_HX_REQUEST="true",
    )
    assert resp.status_code == 200
    assert b'aria-pressed="true"' in resp.content
    assert Availability.objects.filter(volunteer=vol).count() == 1


@pytest.mark.django_db
def test_htmx_toggle_second_call_removes_and_marks_unpressed(client):
    vol = VolunteerFactory()
    client.force_login(vol)
    client.post(
        reverse("volunteers:availability_toggle"),
        data={"day": "mon", "phrase": "morning"},
        HTTP_HX_REQUEST="true",
    )
    resp = client.post(
        reverse("volunteers:availability_toggle"),
        data={"day": "mon", "phrase": "morning"},
        HTTP_HX_REQUEST="true",
    )
    assert resp.status_code == 200
    assert b'aria-pressed="false"' in resp.content
    assert Availability.objects.count() == 0
