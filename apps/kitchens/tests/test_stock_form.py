from datetime import date, timedelta
from decimal import Decimal

import pytest

from apps.kitchens.forms.stock import StockReceiveForm
from apps.kitchens.tests.factories import IngredientFactory, KitchenFactory


pytestmark = pytest.mark.django_db


class TestStockReceiveForm:
    def test_valid_data(self):
        kitchen = KitchenFactory()
        ing = IngredientFactory()
        form = StockReceiveForm(
            data={
                "kitchen": kitchen.pk,
                "ingredient": ing.pk,
                "quantity": "5.00",
                "received_at": str(date.today()),
                "expiration_date": str(date.today() + timedelta(days=10)),
                "lot_number": "LOT-1",
            }
        )
        assert form.is_valid(), form.errors

    def test_expiration_required(self):
        form = StockReceiveForm(
            data={
                "kitchen": KitchenFactory().pk,
                "ingredient": IngredientFactory().pk,
                "quantity": "5.00",
                "received_at": str(date.today()),
                "expiration_date": "",
            }
        )
        assert not form.is_valid()
        assert "expiration_date" in form.errors

    def test_quantity_must_be_positive(self):
        form = StockReceiveForm(
            data={
                "kitchen": KitchenFactory().pk,
                "ingredient": IngredientFactory().pk,
                "quantity": "0",
                "received_at": str(date.today()),
                "expiration_date": str(date.today() + timedelta(days=1)),
            }
        )
        assert not form.is_valid()
        assert "quantity" in form.errors

    def test_expiration_before_received_rejected(self):
        form = StockReceiveForm(
            data={
                "kitchen": KitchenFactory().pk,
                "ingredient": IngredientFactory().pk,
                "quantity": "5.00",
                "received_at": str(date.today()),
                "expiration_date": str(date.today() - timedelta(days=1)),
            }
        )
        assert not form.is_valid()
        assert "expiration_date" in form.errors
