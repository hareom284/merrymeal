from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError

from apps.kitchens.models import IngredientBatch
from apps.kitchens.services.stock import receive_batch
from apps.kitchens.tests.factories import IngredientFactory, KitchenFactory


pytestmark = pytest.mark.django_db


@pytest.fixture
def kitchen():
    return KitchenFactory()


@pytest.fixture
def rice():
    return IngredientFactory(name="Rice", unit="kg")


class TestReceiveBatch:
    def test_creates_one_batch(self, kitchen, rice):
        batch = receive_batch(
            user=None,
            kitchen=kitchen,
            ingredient=rice,
            quantity=Decimal("10.00"),
            expiration_date=date.today() + timedelta(days=14),
        )
        assert IngredientBatch.objects.count() == 1
        assert batch.quantity == Decimal("10.00")
        assert batch.received_at == date.today()

    def test_optional_lot_number_is_stored(self, kitchen, rice):
        batch = receive_batch(
            user=None,
            kitchen=kitchen,
            ingredient=rice,
            quantity=Decimal("5.00"),
            expiration_date=date.today() + timedelta(days=7),
            lot_number="LOT-XYZ",
        )
        assert batch.lot_number == "LOT-XYZ"

    def test_quantity_zero_rejected(self, kitchen, rice):
        with pytest.raises(ValidationError):
            receive_batch(
                user=None,
                kitchen=kitchen,
                ingredient=rice,
                quantity=Decimal("0"),
                expiration_date=date.today() + timedelta(days=7),
            )
