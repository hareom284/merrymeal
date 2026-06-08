from decimal import Decimal

import pytest
from django.contrib.admin.sites import site
from django.core.exceptions import ValidationError

from apps.kitchens.models import Kitchen
from apps.kitchens.tests.factories import KitchenFactory

pytestmark = pytest.mark.django_db


class TestKitchenModel:
    def test_str_is_name(self):
        k = KitchenFactory(name="Footscray Kitchen")
        assert str(k) == "Footscray Kitchen"

    def test_default_service_radius_is_10(self):
        k = Kitchen.objects.create(
            name="St Kilda Kitchen",
            latitude=Decimal("-37.8676"),
            longitude=Decimal("144.9810"),
        )
        assert k.service_radius_km == Decimal("10.00")

    def test_db_table_matches_schema(self):
        assert Kitchen._meta.db_table == "kitchens"

    @pytest.mark.parametrize("lat", [Decimal("-91"), Decimal("90.0000001")])
    def test_latitude_out_of_range_rejected(self, lat):
        k = KitchenFactory.build(latitude=lat)
        with pytest.raises(ValidationError):
            k.full_clean()

    @pytest.mark.parametrize("lng", [Decimal("-181"), Decimal("180.0000001")])
    def test_longitude_out_of_range_rejected(self, lng):
        k = KitchenFactory.build(longitude=lng)
        with pytest.raises(ValidationError):
            k.full_clean()


class TestKitchenAdmin:
    def test_kitchen_is_registered(self):
        assert site.is_registered(Kitchen)

    def test_admin_list_display_columns(self):
        admin = site._registry[Kitchen]
        assert "name" in admin.list_display
        assert "is_outsourced" in admin.list_display
        assert "latitude" in admin.list_display
        assert "longitude" in admin.list_display
        assert "service_radius_km" in admin.list_display
