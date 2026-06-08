from datetime import date, timedelta
from decimal import Decimal

import pytest

from apps.kitchens.services.expiry import find_expiring_batches
from apps.kitchens.tests.factories import (
    IngredientBatchFactory,
    IngredientFactory,
    KitchenFactory,
)

pytestmark = pytest.mark.django_db


def test_returns_batches_within_window():
    kitchen = KitchenFactory()
    ing = IngredientFactory()
    today = date.today()
    in_2 = IngredientBatchFactory(kitchen=kitchen, ingredient=ing,
                                  expiration_date=today + timedelta(days=2),
                                  quantity=Decimal("1.00"))
    in_5 = IngredientBatchFactory(kitchen=kitchen, ingredient=ing,
                                  expiration_date=today + timedelta(days=5),
                                  quantity=Decimal("1.00"))

    rows = list(find_expiring_batches(kitchen, within_days=3))
    assert in_2 in rows
    assert in_5 not in rows


def test_excludes_zero_quantity_batches():
    kitchen = KitchenFactory()
    today = date.today()
    empty = IngredientBatchFactory(kitchen=kitchen,
                                   expiration_date=today + timedelta(days=1),
                                   quantity=Decimal("0.00"))
    assert empty not in list(find_expiring_batches(kitchen, within_days=3))


def test_excludes_other_kitchens():
    a, b = KitchenFactory(), KitchenFactory()
    today = date.today()
    a_batch = IngredientBatchFactory(kitchen=a,
                                     expiration_date=today + timedelta(days=1),
                                     quantity=Decimal("1.00"))
    b_batch = IngredientBatchFactory(kitchen=b,
                                     expiration_date=today + timedelta(days=1),
                                     quantity=Decimal("1.00"))
    rows = list(find_expiring_batches(a, within_days=3))
    assert a_batch in rows
    assert b_batch not in rows


def test_orders_by_ingredient_then_expiry():
    kitchen = KitchenFactory()
    rice = IngredientFactory(name="Rice")
    onion = IngredientFactory(name="Onion")
    today = date.today()
    IngredientBatchFactory(kitchen=kitchen, ingredient=rice,
                           expiration_date=today + timedelta(days=1),
                           quantity=Decimal("1.00"))
    IngredientBatchFactory(kitchen=kitchen, ingredient=rice,
                           expiration_date=today + timedelta(days=2),
                           quantity=Decimal("1.00"))
    IngredientBatchFactory(kitchen=kitchen, ingredient=onion,
                           expiration_date=today + timedelta(days=2),
                           quantity=Decimal("1.00"))
    rows = list(find_expiring_batches(kitchen, within_days=3))
    assert rows == sorted(rows, key=lambda b: (b.ingredient_id, b.expiration_date))
