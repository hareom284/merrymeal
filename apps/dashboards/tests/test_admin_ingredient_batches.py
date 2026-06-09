"""Tests for the admin ingredient-batch browser + add-new (Story 12.16)."""
from datetime import date, timedelta
from decimal import Decimal

import pytest

from apps.accounts.tests.factories import UserFactory
from apps.kitchens.models import IngredientBatch
from apps.kitchens.tests.factories import IngredientFactory, KitchenFactory


def _make_batch(*, kitchen=None, ingredient=None, expires_in_days=10, qty="5.00"):
    """Helper — write the row directly so tests control ``expiration_date``
    precisely (the kitchen-staff service derives ``received_at`` from
    today by default)."""
    return IngredientBatch.objects.create(
        kitchen=kitchen or KitchenFactory(),
        ingredient=ingredient or IngredientFactory(),
        quantity=Decimal(qty),
        expiration_date=date.today() + timedelta(days=expires_in_days),
        received_at=date.today(),
    )


@pytest.mark.django_db
def test_batches_list_requires_admin(client):
    user = UserFactory(role="kitchen_staff")
    client.force_login(user)
    response = client.get("/admin/stock/")
    assert response.status_code == 403


@pytest.mark.django_db
def test_batches_list_renders_with_seed_batches(client):
    admin = UserFactory(role="admin")
    k = KitchenFactory(name="Carlton")
    i = IngredientFactory(name="Flour")
    _make_batch(kitchen=k, ingredient=i)
    client.force_login(admin)
    response = client.get("/admin/stock/")
    assert response.status_code == 200
    body = response.content
    assert b"Carlton" in body
    assert b"Flour" in body


@pytest.mark.django_db
def test_batches_list_filter_by_kitchen(client):
    admin = UserFactory(role="admin")
    k1 = KitchenFactory(name="K1")
    k2 = KitchenFactory(name="K2")
    b1 = _make_batch(kitchen=k1)
    b2 = _make_batch(kitchen=k2)
    client.force_login(admin)
    response = client.get("/admin/stock/", {"kitchen": k1.id})
    body = response.content
    assert f"/admin/stock/{b1.id}/".encode() in body
    assert f"/admin/stock/{b2.id}/".encode() not in body


@pytest.mark.django_db
def test_batches_list_filter_expired_only(client):
    """``?expiring=expired`` narrows to batches whose expiration_date is
    strictly in the past. Same-day batches are NOT expired (they expire
    at end-of-day in business terms)."""
    admin = UserFactory(role="admin")
    expired = _make_batch(expires_in_days=-2)
    fresh = _make_batch(expires_in_days=5)
    client.force_login(admin)
    response = client.get("/admin/stock/", {"expiring": "expired"})
    body = response.content
    assert f"/admin/stock/{expired.id}/".encode() in body
    assert f"/admin/stock/{fresh.id}/".encode() not in body


@pytest.mark.django_db
def test_batches_list_filter_expiring_within_3_days(client):
    admin = UserFactory(role="admin")
    soon = _make_batch(expires_in_days=2)
    later = _make_batch(expires_in_days=10)
    client.force_login(admin)
    response = client.get("/admin/stock/", {"expiring": "3"})
    body = response.content
    assert f"/admin/stock/{soon.id}/".encode() in body
    assert f"/admin/stock/{later.id}/".encode() not in body


@pytest.mark.django_db
def test_batches_ordered_soonest_expiring_first(client):
    admin = UserFactory(role="admin")
    later = _make_batch(expires_in_days=14)
    soon = _make_batch(expires_in_days=2)
    client.force_login(admin)
    body = client.get("/admin/stock/").content
    soon_pos = body.index(f"/admin/stock/{soon.id}/".encode())
    later_pos = body.index(f"/admin/stock/{later.id}/".encode())
    assert soon_pos < later_pos


@pytest.mark.django_db
def test_batch_detail_renders(client):
    admin = UserFactory(role="admin")
    batch = _make_batch()
    client.force_login(admin)
    response = client.get(f"/admin/stock/{batch.id}/")
    assert response.status_code == 200


@pytest.mark.django_db
def test_batch_detail_404_for_unknown_id(client):
    admin = UserFactory(role="admin")
    client.force_login(admin)
    response = client.get("/admin/stock/9999999/")
    assert response.status_code == 404


@pytest.mark.django_db
def test_batch_create_get_renders_form(client):
    admin = UserFactory(role="admin")
    KitchenFactory()
    IngredientFactory()
    client.force_login(admin)
    response = client.get("/admin/stock/new/")
    assert response.status_code == 200
    assert b"Log batch" in response.content


@pytest.mark.django_db
def test_batch_create_post_persists_via_receive_batch(client):
    """The admin create path must flow through ``receive_batch`` so the
    audit-logged write is consistent with the kitchen-staff path."""
    admin = UserFactory(role="admin")
    kitchen = KitchenFactory()
    ingredient = IngredientFactory()
    client.force_login(admin)
    response = client.post("/admin/stock/new/", {
        "kitchen": kitchen.id,
        "ingredient": ingredient.id,
        "quantity": "12.50",
        "received_at": date.today().isoformat(),
        "expiration_date": (date.today() + timedelta(days=14)).isoformat(),
        "lot_number": "LOT-1",
    })
    assert response.status_code == 302
    batch = IngredientBatch.objects.get(lot_number="LOT-1")
    assert batch.quantity == Decimal("12.50")
    assert batch.kitchen_id == kitchen.id


@pytest.mark.django_db
def test_batch_create_rejects_zero_quantity(client):
    """``receive_batch`` calls full_clean(); the MinValueValidator on
    quantity (0.01) fires on receive. The form should re-render with
    an error rather than 500."""
    admin = UserFactory(role="admin")
    kitchen = KitchenFactory()
    ingredient = IngredientFactory()
    client.force_login(admin)
    response = client.post("/admin/stock/new/", {
        "kitchen": kitchen.id,
        "ingredient": ingredient.id,
        "quantity": "0.00",
        "received_at": date.today().isoformat(),
        "expiration_date": (date.today() + timedelta(days=14)).isoformat(),
        "lot_number": "",
    })
    assert response.status_code == 200
    assert IngredientBatch.objects.count() == 0


@pytest.mark.django_db
def test_admin_home_links_to_batches(client):
    admin = UserFactory(role="admin")
    client.force_login(admin)
    response = client.get("/admin/home/")
    assert b"/admin/stock/" in response.content


@pytest.mark.django_db
def test_admin_stock_has_no_edit_or_delete_routes():
    """Design contract: stock records are immutable. Corrections happen
    via separate deduction/write-off events, not edit."""
    from django.urls import NoReverseMatch, reverse

    for name in ("dashboards:admin_batch_edit", "dashboards:admin_batch_delete"):
        with pytest.raises(NoReverseMatch):
            reverse(name)
