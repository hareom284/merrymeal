import pytest
from django.urls import reverse

from apps.accounts.tests.factories import UserFactory
from apps.food_safety.models import FoodSafetyCheck
from apps.food_safety.services.checks import record_check
from apps.kitchens.tests.factories import KitchenFactory


pytestmark = pytest.mark.django_db
URL = "/kitchen/safety/check/"


def test_anonymous_redirects_to_login(client):
    response = client.get(URL)
    assert response.status_code == 302
    assert "/accounts/login/" in response["Location"]


def test_member_role_gets_403(client):
    user = UserFactory(role="member")
    client.force_login(user)
    response = client.get(URL)
    assert response.status_code == 403


def test_kitchen_staff_can_load_form(client):
    user = UserFactory(role="kitchen_staff")
    client.force_login(user)
    response = client.get(URL)
    assert response.status_code == 200
    assert b'name="check_type"' in response.content


def test_post_creates_check_and_redirects(client):
    user = UserFactory(role="kitchen_staff")
    kitchen = KitchenFactory()
    client.force_login(user)
    response = client.post(URL, {
        "kitchen": kitchen.id,
        "check_type": "storage_temp",
        "temperature_celsius": "4.0",
        "result": "",
        "notes": "Walk-in.",
    })
    assert response.status_code == 302
    assert FoodSafetyCheck.objects.count() == 1
    row = FoodSafetyCheck.objects.get()
    assert row.checked_by_id == user.id
    assert row.result == "pass"


def test_already_done_today_appears_at_top(client):
    user = UserFactory(role="kitchen_staff")
    kitchen = KitchenFactory()
    record_check(
        kitchen=kitchen, user=user,
        check_type="hygiene", temperature_celsius=None,
        result="pass", notes="ok",
    )
    client.force_login(user)
    response = client.get(URL)
    assert response.status_code == 200
    body = response.content.decode()
    assert "Already done today" in body
    assert "hygiene" in body.lower()
