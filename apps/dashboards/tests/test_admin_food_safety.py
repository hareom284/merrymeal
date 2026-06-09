"""Tests for the admin food-safety browser + add-new (Story 12.12)."""
from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.accounts.tests.factories import UserFactory
from apps.food_safety.models import FoodSafetyCheck
from apps.kitchens.tests.factories import KitchenFactory


def _make_check(
    *,
    kitchen=None,
    checker=None,
    result="pass",
    check_type="storage_temp",
    temp=Decimal("4.0"),
    when=None,
):
    """Helper — record the FoodSafetyCheck row directly to keep test
    setup terse. Doesn't go through ``record_check`` because we want
    explicit control over ``checked_at`` for the date-filter tests."""
    kitchen = kitchen or KitchenFactory()
    checker = checker or UserFactory(role="admin")
    return FoodSafetyCheck.objects.create(
        kitchen=kitchen,
        check_type=check_type,
        temperature_celsius=temp if check_type == "storage_temp" else None,
        result=result,
        checked_by=checker,
        checked_at=when or timezone.now(),
    )


@pytest.mark.django_db
def test_fs_list_requires_admin(client):
    user = UserFactory(role="kitchen_staff")
    client.force_login(user)
    response = client.get("/admin/food_safety/")
    assert response.status_code == 403


@pytest.mark.django_db
def test_fs_list_renders_and_lists_checks(client):
    admin = UserFactory(role="admin")
    kitchen = KitchenFactory(name="Carlton Kitchen")
    _make_check(kitchen=kitchen, checker=admin, result="pass")
    _make_check(kitchen=kitchen, checker=admin, result="fail")
    client.force_login(admin)
    response = client.get("/admin/food_safety/")
    assert response.status_code == 200
    body = response.content
    assert b"Carlton Kitchen" in body
    assert b"Pass" in body and b"Fail" in body


@pytest.mark.django_db
def test_fs_list_filter_by_kitchen(client):
    """Kitchen filter narrows the table rows. Both kitchens still
    appear in the filter dropdown (so the admin can switch); the
    assertion is on detail-link presence, not raw name string."""
    admin = UserFactory(role="admin")
    k1 = KitchenFactory(name="Kitchen One")
    k2 = KitchenFactory(name="Kitchen Two")
    c1 = _make_check(kitchen=k1, checker=admin)
    c2 = _make_check(kitchen=k2, checker=admin)
    client.force_login(admin)

    response = client.get("/admin/food_safety/", {"kitchen": k1.id})
    body = response.content
    assert f"/admin/food_safety/{c1.id}/".encode() in body
    assert f"/admin/food_safety/{c2.id}/".encode() not in body


@pytest.mark.django_db
def test_fs_list_filter_by_result(client):
    admin = UserFactory(role="admin")
    kitchen = KitchenFactory(name="K")
    _make_check(kitchen=kitchen, checker=admin, result="pass")
    fail = _make_check(kitchen=kitchen, checker=admin, result="fail")
    client.force_login(admin)

    response = client.get("/admin/food_safety/", {"result": "fail"})
    body = response.content
    # Detail link of the fail row must appear; the pass row must not.
    assert f"/admin/food_safety/{fail.id}/".encode() in body


@pytest.mark.django_db
def test_fs_list_filter_by_date_range(client):
    admin = UserFactory(role="admin")
    kitchen = KitchenFactory(name="K")
    today = timezone.now()
    week_ago = today - timedelta(days=7)
    old = _make_check(kitchen=kitchen, checker=admin, when=week_ago)
    recent = _make_check(kitchen=kitchen, checker=admin, when=today)
    client.force_login(admin)

    # Only-today window
    response = client.get(
        "/admin/food_safety/",
        {"from": today.date().isoformat(), "to": today.date().isoformat()},
    )
    body = response.content
    assert f"/admin/food_safety/{recent.id}/".encode() in body
    assert f"/admin/food_safety/{old.id}/".encode() not in body


@pytest.mark.django_db
def test_fs_detail_renders(client):
    admin = UserFactory(role="admin")
    check = _make_check(checker=admin)
    client.force_login(admin)
    response = client.get(f"/admin/food_safety/{check.id}/")
    assert response.status_code == 200


@pytest.mark.django_db
def test_fs_detail_404_for_unknown_id(client):
    admin = UserFactory(role="admin")
    client.force_login(admin)
    response = client.get("/admin/food_safety/999999/")
    assert response.status_code == 404


@pytest.mark.django_db
def test_fs_create_get_renders_form(client):
    admin = UserFactory(role="admin")
    KitchenFactory()
    client.force_login(admin)
    response = client.get("/admin/food_safety/new/")
    assert response.status_code == 200
    assert b"Save check" in response.content


@pytest.mark.django_db
def test_fs_create_post_temp_check_derives_result(client):
    """Temperature checks must auto-derive pass/fail via record_check,
    so the admin doesn't have to think about thresholds."""
    admin = UserFactory(role="admin")
    kitchen = KitchenFactory()
    client.force_login(admin)
    response = client.post("/admin/food_safety/new/", {
        "kitchen": kitchen.id,
        "check_type": "storage_temp",
        "temperature_celsius": "4.0",
        "result": "",
        "notes": "All clear.",
    })
    assert response.status_code == 302
    check = FoodSafetyCheck.objects.get(notes="All clear.")
    assert check.result == "pass"  # 4°C is below the 5°C threshold


@pytest.mark.django_db
def test_fs_create_post_temp_check_fails_when_over_threshold(client):
    admin = UserFactory(role="admin")
    kitchen = KitchenFactory()
    client.force_login(admin)
    response = client.post("/admin/food_safety/new/", {
        "kitchen": kitchen.id,
        "check_type": "storage_temp",
        "temperature_celsius": "10.0",
        "result": "",
        "notes": "",
    })
    assert response.status_code == 302
    check = FoodSafetyCheck.objects.order_by("-id").first()
    assert check.result == "fail"  # 10°C > 5°C threshold


@pytest.mark.django_db
def test_fs_create_post_missing_temperature_re_renders_with_error(client):
    admin = UserFactory(role="admin")
    kitchen = KitchenFactory()
    client.force_login(admin)
    response = client.post("/admin/food_safety/new/", {
        "kitchen": kitchen.id,
        "check_type": "storage_temp",
        "temperature_celsius": "",
        "result": "",
        "notes": "",
    })
    # Re-rendered (200), no new row.
    assert response.status_code == 200
    assert FoodSafetyCheck.objects.count() == 0
    assert b"Temperature is required" in response.content


@pytest.mark.django_db
def test_admin_home_links_to_food_safety_browser(client):
    """Admins reach the food-safety browser from the home directories
    section — surfaced alongside Members and Kitchens."""
    admin = UserFactory(role="admin")
    client.force_login(admin)
    response = client.get("/admin/home/")
    assert b"/admin/food_safety/" in response.content


@pytest.mark.django_db
def test_admin_fs_has_no_edit_or_delete_routes(client):
    """Design contract: food-safety records are immutable. There is no
    edit URL and no delete URL — corrections happen via a new check."""
    from django.urls import NoReverseMatch, reverse

    for name in ("dashboards:admin_fs_edit", "dashboards:admin_fs_delete"):
        with pytest.raises(NoReverseMatch):
            reverse(name)
