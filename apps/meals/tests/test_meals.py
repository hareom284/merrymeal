import pytest
from django.contrib.admin.sites import site
from django.utils import timezone

from apps.meals.models import Meal
from apps.meals.tests.factories import MealFactory

pytestmark = pytest.mark.django_db


class TestMealModel:
    def test_str_is_name(self):
        m = MealFactory(name="Pumpkin curry")
        assert str(m) == "Pumpkin curry"

    def test_db_table(self):
        assert Meal._meta.db_table == "meals"

    def test_defaults(self):
        m = Meal.objects.create(name="Plain rice")
        assert m.is_active is True
        assert m.description is None
        assert m.prep_time_minutes is None
        assert m.cook_time_minutes is None
        assert m.deleted_at is None

    def test_soft_delete_hides_from_default_manager(self):
        m = MealFactory()
        assert Meal.objects.filter(pk=m.pk).exists()
        m.deleted_at = timezone.now()
        m.save(update_fields=["deleted_at"])
        assert not Meal.objects.filter(pk=m.pk).exists()
        assert Meal.all_objects.filter(pk=m.pk).exists()


class TestMealAdmin:
    def test_meal_is_registered(self):
        assert site.is_registered(Meal)

    def test_admin_list_display(self):
        admin = site._registry[Meal]
        assert "name" in admin.list_display
        assert "prep_time_minutes" in admin.list_display
        assert "cook_time_minutes" in admin.list_display
        assert "is_active" in admin.list_display

    def test_admin_filters_by_is_active(self):
        admin = site._registry[Meal]
        assert "is_active" in admin.list_filter
