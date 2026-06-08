from decimal import Decimal

import pytest
from django.contrib import admin as django_admin

from apps.accounts.models import Address, User
from apps.accounts.tests.factories import CityFactory, UserFactory


@pytest.mark.django_db
def test_address_can_be_created_with_required_fields():
    user = UserFactory()
    city = CityFactory(name="Melbourne")
    addr = Address.objects.create(
        user=user,
        city=city,
        label="Home",
        postal_code="3000",
    )
    assert addr.pk is not None
    assert addr.user_id == user.pk
    assert addr.city_id == city.pk
    assert addr.label == "Home"
    assert addr.postal_code == "3000"
    assert addr.latitude is None
    assert addr.longitude is None


@pytest.mark.django_db
def test_address_accepts_decimal_lat_lng():
    user = UserFactory()
    city = CityFactory(name="Geelong")
    addr = Address.objects.create(
        user=user,
        city=city,
        latitude=Decimal("-37.8136111"),
        longitude=Decimal("144.9630580"),
    )
    addr.refresh_from_db()
    assert addr.latitude == Decimal("-37.8136111")
    assert addr.longitude == Decimal("144.9630580")


@pytest.mark.django_db
def test_address_db_table_is_user_addresses():
    assert Address._meta.db_table == "user_addresses"


@pytest.mark.django_db
def test_address_lat_lng_decimal_precision():
    fields = {f.name: f for f in Address._meta.get_fields() if hasattr(f, "max_digits")}
    assert fields["latitude"].max_digits == 10
    assert fields["latitude"].decimal_places == 7
    assert fields["latitude"].null is True
    assert fields["longitude"].max_digits == 10
    assert fields["longitude"].decimal_places == 7
    assert fields["longitude"].null is True


@pytest.mark.django_db
def test_user_can_have_many_addresses():
    user = UserFactory()
    city = CityFactory(name="Ballarat")
    Address.objects.create(user=user, city=city, label="Home", postal_code="3350")
    Address.objects.create(user=user, city=city, label="Daughter", postal_code="3355")
    assert Address.objects.filter(user=user).count() == 2


@pytest.mark.django_db
def test_address_str_includes_label_and_postal_code():
    user = UserFactory()
    city = CityFactory(name="Bendigo")
    addr = Address.objects.create(
        user=user, city=city, label="Home", postal_code="3550"
    )
    s = str(addr)
    assert "Home" in s
    assert "3550" in s


def test_address_inline_is_registered_on_user_admin():
    user_admin = django_admin.site._registry[User]
    inline_models = [inline.model for inline in user_admin.inlines]
    assert Address in inline_models


def test_address_inline_uses_tabular_layout_with_no_extra_blank_rows():
    user_admin = django_admin.site._registry[User]
    address_inline_cls = next(
        inline for inline in user_admin.inlines if inline.model is Address
    )
    from django.contrib.admin import TabularInline
    assert issubclass(address_inline_cls, TabularInline)
    assert address_inline_cls.extra == 0
