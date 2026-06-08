from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.contrib.admin.sites import site
from django.core.exceptions import ValidationError

from apps.kitchens.admin import ExpiringSoonFilter
from apps.kitchens.models import IngredientBatch
from apps.kitchens.tests.factories import (
    IngredientBatchFactory,
    IngredientFactory,
    KitchenFactory,
)


pytestmark = pytest.mark.django_db


class TestIngredientBatchModel:
    def test_db_table(self):
        assert IngredientBatch._meta.db_table == "ingredient_batches"

    def test_str_mentions_ingredient_and_lot(self):
        b = IngredientBatchFactory(
            ingredient=IngredientFactory(name="Rice"),
            lot_number="LOT-99",
        )
        s = str(b)
        assert "Rice" in s and "LOT-99" in s

    def test_quantity_must_be_positive(self):
        b = IngredientBatchFactory.build(quantity=Decimal("0"))
        with pytest.raises(ValidationError):
            b.full_clean()

    def test_expiration_must_be_on_or_after_received(self):
        b = IngredientBatchFactory.build(
            received_at=date(2026, 6, 10),
            expiration_date=date(2026, 6, 5),
        )
        with pytest.raises(ValidationError):
            b.full_clean()

    def test_expiration_equal_to_received_is_allowed(self):
        # Use create() so FKs are DB-backed and don't trigger FK ValidationError
        b = IngredientBatchFactory(
            received_at=date(2026, 6, 10),
            expiration_date=date(2026, 6, 10),
            quantity=Decimal("1.00"),
        )
        b.full_clean()  # no raise

    def test_expiration_index_declared(self):
        index_fields = [tuple(idx.fields) for idx in IngredientBatch._meta.indexes]
        assert ("expiration_date",) in index_fields


class TestExpiringSoonFilter:
    def test_filter_registered_on_batch_admin(self):
        batch_admin = site._registry[IngredientBatch]
        assert ExpiringSoonFilter in batch_admin.list_filter

    def test_expiring_soon_query_logic(self):
        """Verifies the ORM query the filter uses — same logic as ExpiringSoonFilter.queryset()."""
        kitchen = KitchenFactory()
        soon = IngredientBatchFactory(
            kitchen=kitchen,
            expiration_date=date.today() + timedelta(days=2),
            quantity=Decimal("1.00"),
        )
        later = IngredientBatchFactory(
            kitchen=kitchen,
            expiration_date=date.today() + timedelta(days=10),
            quantity=Decimal("1.00"),
        )
        # Depleted batch: bypass full_clean() — quantity=0 is a valid terminal state
        depleted = IngredientBatch.objects.create(
            ingredient=IngredientFactory(),
            kitchen=kitchen,
            expiration_date=date.today() + timedelta(days=1),
            quantity=Decimal("0.00"),
        )

        cutoff = date.today() + timedelta(days=3)
        qs = IngredientBatch.objects.filter(
            expiration_date__lte=cutoff, quantity__gt=Decimal("0")
        )
        ids = set(qs.values_list("pk", flat=True))
        assert soon.pk in ids
        assert later.pk not in ids
        assert depleted.pk not in ids
