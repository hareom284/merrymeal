import datetime as dt

import pytest

from apps.accounts.tests.factories import UserFactory
from apps.kitchens.tests.factories import KitchenFactory
from apps.meals.tests.factories import MealFactory
from apps.planning.models import MealPlan
from apps.planning.tests.factories import MealPlanFactory


@pytest.mark.django_db
class TestAdminPlannerAccess:
    def test_anonymous_redirected_to_login(self, client):
        resp = client.get("/admin/planner/")
        assert resp.status_code in (302, 403)

    def test_member_forbidden(self, client):
        client.force_login(UserFactory(role="member"))
        resp = client.get("/admin/planner/")
        assert resp.status_code in (302, 403)

    def test_admin_ok(self, client):
        client.force_login(UserFactory(role="admin"))
        resp = client.get("/admin/planner/")
        assert resp.status_code == 200


@pytest.mark.django_db
class TestAdminPlannerGrid:
    def test_default_week_is_next_week(self, client, monkeypatch):
        # Freeze "today" to Wednesday 2026-06-03; next Monday is 2026-06-08.
        import apps.planning.views.admin_planner as view_mod

        class _FakeTZ:
            @staticmethod
            def localdate():
                return dt.date(2026, 6, 3)

        monkeypatch.setattr(view_mod, "timezone", _FakeTZ)
        client.force_login(UserFactory(role="admin"))
        resp = client.get("/admin/planner/")
        assert resp.status_code == 200
        assert b"2026-06-08" in resp.content

    def test_week_param_navigates(self, client):
        client.force_login(UserFactory(role="admin"))
        resp = client.get("/admin/planner/?week=2026-06-15")
        assert resp.status_code == 200
        assert b"2026-06-15" in resp.content  # Monday

    def test_week_param_snaps_to_monday(self, client):
        # 2026-06-17 is a Wednesday; Monday of that week is 2026-06-15.
        client.force_login(UserFactory(role="admin"))
        resp = client.get("/admin/planner/?week=2026-06-17")
        assert resp.status_code == 200
        assert b"2026-06-15" in resp.content

    def test_invalid_week_param_400(self, client):
        client.force_login(UserFactory(role="admin"))
        resp = client.get("/admin/planner/?week=banana")
        assert resp.status_code == 400

    def test_grid_shows_existing_meal_name(self, client):
        client.force_login(UserFactory(role="admin"))
        plan = MealPlanFactory(service_date=dt.date(2026, 6, 15))
        resp = client.get("/admin/planner/?week=2026-06-15")
        assert resp.status_code == 200
        assert plan.meal.name.encode() in resp.content


@pytest.mark.django_db
class TestUpsertCellService:
    def test_create_sets_meal_type_fresh_on_weekday(self):
        from apps.planning.services.planner import upsert_cell

        kitchen = KitchenFactory()
        meal = MealFactory()
        admin = UserFactory(role="admin")
        plan = upsert_cell(
            kitchen=kitchen,
            meal=meal,
            service_date=dt.date(2026, 6, 3),  # Wed
            planned_quantity=25,
            published_by=admin,
        )
        assert plan.meal_type == "fresh"
        assert plan.day_of_week == "wed"
        assert plan.planned_quantity == 25
        assert plan.published_by_id == admin.id

    def test_create_sets_meal_type_frozen_on_saturday(self):
        from apps.planning.services.planner import upsert_cell

        plan = upsert_cell(
            kitchen=KitchenFactory(),
            meal=MealFactory(),
            service_date=dt.date(2026, 6, 6),  # Sat
            planned_quantity=10,
            published_by=UserFactory(role="admin"),
        )
        assert plan.meal_type == "frozen"
        assert plan.day_of_week == "sat"

    def test_create_sets_meal_type_frozen_on_sunday(self):
        from apps.planning.services.planner import upsert_cell

        plan = upsert_cell(
            kitchen=KitchenFactory(),
            meal=MealFactory(),
            service_date=dt.date(2026, 6, 7),  # Sun
            planned_quantity=12,
            published_by=UserFactory(role="admin"),
        )
        assert plan.meal_type == "frozen"
        assert plan.day_of_week == "sun"

    def test_update_existing_cell(self):
        from apps.planning.services.planner import upsert_cell

        existing = MealPlanFactory(service_date=dt.date(2026, 6, 3))
        new_meal = MealFactory()
        plan = upsert_cell(
            kitchen=existing.kitchen,
            meal=new_meal,
            service_date=existing.service_date,
            planned_quantity=99,
            published_by=existing.published_by,
        )
        assert plan.pk == existing.pk
        assert plan.meal_id == new_meal.id
        assert plan.planned_quantity == 99
        assert (
            MealPlan.objects.filter(
                kitchen=existing.kitchen, service_date=existing.service_date
            ).count()
            == 1
        )


@pytest.mark.django_db
class TestCellEditView:
    def test_get_returns_modal_form_for_empty_cell(self, client):
        admin = UserFactory(role="admin")
        kitchen = KitchenFactory()
        client.force_login(admin)
        resp = client.get(f"/admin/planner/cell/?kitchen={kitchen.id}&date=2026-06-03")
        assert resp.status_code == 200
        assert b"<form" in resp.content
        assert b"planned_quantity" in resp.content

    def test_get_returns_form_prefilled_for_populated_cell(self, client):
        admin = UserFactory(role="admin")
        plan = MealPlanFactory(service_date=dt.date(2026, 6, 3), planned_quantity=42)
        client.force_login(admin)
        resp = client.get(
            f"/admin/planner/cell/?kitchen={plan.kitchen_id}&date=2026-06-03"
        )
        assert resp.status_code == 200
        assert b"42" in resp.content

    def test_post_creates_meal_plan_and_returns_cell_partial(self, client):
        admin = UserFactory(role="admin")
        kitchen = KitchenFactory()
        meal = MealFactory()
        client.force_login(admin)
        resp = client.post(
            f"/admin/planner/cell/?kitchen={kitchen.id}&date=2026-06-03",
            data={"meal": meal.id, "planned_quantity": 30},
        )
        assert resp.status_code == 200
        assert meal.name.encode() in resp.content
        plan = MealPlan.objects.get(kitchen=kitchen, service_date=dt.date(2026, 6, 3))
        assert plan.planned_quantity == 30
        assert plan.meal_id == meal.id
        assert plan.meal_type == "fresh"
        assert plan.day_of_week == "wed"
        assert plan.published_by_id == admin.id

    def test_post_updates_existing_meal_plan(self, client):
        admin = UserFactory(role="admin")
        existing = MealPlanFactory(
            service_date=dt.date(2026, 6, 3), planned_quantity=5
        )
        new_meal = MealFactory()
        client.force_login(admin)
        resp = client.post(
            f"/admin/planner/cell/?kitchen={existing.kitchen_id}&date=2026-06-03",
            data={"meal": new_meal.id, "planned_quantity": 50},
        )
        assert resp.status_code == 200
        existing.refresh_from_db()
        assert existing.planned_quantity == 50
        assert existing.meal_id == new_meal.id

    def test_post_with_bad_kitchen_or_date_400(self, client):
        client.force_login(UserFactory(role="admin"))
        resp = client.get("/admin/planner/cell/?kitchen=notanint&date=2026-06-03")
        assert resp.status_code == 400

    def test_member_forbidden_from_cell_edit(self, client):
        client.force_login(UserFactory(role="member"))
        resp = client.get("/admin/planner/cell/?kitchen=1&date=2026-06-03")
        assert resp.status_code in (302, 403)


@pytest.mark.django_db
class TestMealPlanCellForm:
    def test_form_valid_with_active_meal_and_quantity(self):
        from apps.planning.forms.planner import MealPlanCellForm

        meal = MealFactory()
        form = MealPlanCellForm(data={"meal": meal.id, "planned_quantity": 20})
        assert form.is_valid(), form.errors

    def test_form_rejects_negative_quantity(self):
        from apps.planning.forms.planner import MealPlanCellForm

        meal = MealFactory()
        form = MealPlanCellForm(data={"meal": meal.id, "planned_quantity": -1})
        assert not form.is_valid()
        assert "planned_quantity" in form.errors

    def test_form_excludes_inactive_meals(self):
        from apps.planning.forms.planner import MealPlanCellForm

        inactive = MealFactory(is_active=False)
        form = MealPlanCellForm()
        assert inactive not in form.fields["meal"].queryset
