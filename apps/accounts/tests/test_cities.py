import pytest
from django.contrib import admin as django_admin
from django.core.management import call_command

from apps.accounts.models import City
from apps.core.services import soft_delete


@pytest.mark.django_db
def test_city_can_be_created_with_a_name():
    city = City.objects.create(name="Melbourne")
    assert city.pk is not None
    assert city.name == "Melbourne"
    assert city.created_at is not None
    assert city.updated_at is not None
    assert city.deleted_at is None


@pytest.mark.django_db
def test_city_str_returns_name():
    city = City.objects.create(name="Geelong")
    assert str(city) == "Geelong"


@pytest.mark.django_db
def test_city_db_table_is_cities():
    assert City._meta.db_table == "cities"


@pytest.mark.django_db
def test_city_soft_delete_hides_from_default_manager():
    city = City.objects.create(name="Ballarat")
    soft_delete(city)
    assert City.objects.filter(pk=city.pk).count() == 0
    assert City.all_objects.filter(pk=city.pk).count() == 1


def test_city_is_registered_in_django_admin():
    assert City in django_admin.site._registry
    city_admin = django_admin.site._registry[City]
    assert "name" in city_admin.list_display
    assert "name" in city_admin.search_fields


@pytest.mark.django_db
def test_cities_table_columns_match_schema():
    columns = {f.column: f for f in City._meta.get_fields() if hasattr(f, "column")}
    assert "name" in columns
    assert columns["name"].max_length == 120
    assert "created_at" in columns
    assert "updated_at" in columns
    assert "deleted_at" in columns


@pytest.mark.django_db
def test_seed_cities_creates_the_five_starter_cities():
    call_command("seed_cities")
    names = set(City.objects.values_list("name", flat=True))
    assert names == {"Hlaing", "Insein", "Bahan", "Kamayut", "Yankin"}


@pytest.mark.django_db
def test_seed_cities_is_idempotent():
    call_command("seed_cities")
    call_command("seed_cities")
    assert City.objects.count() == 5
