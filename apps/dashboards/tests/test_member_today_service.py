"""Unit tests for `apps.dashboards.services.member_today.get_today_card`.

Story 3.4 — Member dashboard: today's meal card.
"""
from __future__ import annotations

import datetime as dt
from decimal import Decimal

import pytest

from apps.accounts.tests.factories import UserAddressFactory, UserFactory
from apps.dietary.tests.factories import AllergyFactory
from apps.kitchens.tests.factories import IngredientFactory, KitchenFactory
from apps.meals.tests.factories import MealFactory
from apps.planning.tests.factories import MealPlanFactory

THROUGH_DEFAULTS = {"quantity": Decimal("1.00")}

FROZEN_TODAY = dt.date(2026, 6, 15)


@pytest.fixture
def frozen_today(monkeypatch):
    """Pin ``timezone.localdate()`` to 2026-06-15 inside the service module.

    The story spec uses ``pytest-freezer``; we monkeypatch the imported
    name instead so the suite stays runnable without an extra dev-only
    dep (it isn't installed in every dev environment yet).
    """
    from apps.dashboards.services import member_today as svc

    monkeypatch.setattr(svc.timezone, "localdate", lambda: FROZEN_TODAY)
    return FROZEN_TODAY


@pytest.mark.django_db
class TestGetTodayCard:
    def test_no_plan_returns_empty_state(self, frozen_today):
        from apps.dashboards.services.member_today import get_today_card

        member = UserFactory(role="member")
        UserAddressFactory(user=member, latitude=-37.81, longitude=144.96)
        card = get_today_card(member)
        assert card["has_meal"] is False
        assert "next_plan_date" in card

    def test_card_includes_meal_and_ingredients(self, frozen_today):
        from apps.dashboards.services.member_today import get_today_card

        kitchen = KitchenFactory(
            latitude=-37.81, longitude=144.96, service_radius_km=10
        )
        member = UserFactory(role="member")
        UserAddressFactory(user=member, latitude=-37.82, longitude=144.97)
        meal = MealFactory(name="Herb-roasted chicken")
        meal.ingredients.add(IngredientFactory(name="Chicken thigh"), through_defaults=THROUGH_DEFAULTS)
        meal.ingredients.add(IngredientFactory(name="Olive oil"), through_defaults=THROUGH_DEFAULTS)
        MealPlanFactory(kitchen=kitchen, meal=meal, service_date=frozen_today)

        card = get_today_card(member)
        assert card["has_meal"] is True
        assert card["meal_name"] == "Herb-roasted chicken"
        assert "Chicken thigh" in card["ingredient_names"]
        assert card["delivery_status_label"].startswith("Planned")

    def test_card_flags_member_allergens(self, frozen_today):
        from apps.dashboards.services.member_today import get_today_card

        peanut = AllergyFactory(name="Peanut")
        peanut_ingredient = IngredientFactory(name="Peanut")
        peanut_ingredient.contains_allergens.add(peanut)

        kitchen = KitchenFactory(latitude=-37.81, longitude=144.96)
        member = UserFactory(role="member")
        UserAddressFactory(user=member, latitude=-37.82, longitude=144.97)
        member.allergies.add(peanut)

        meal = MealFactory(name="Satay noodles")
        meal.ingredients.add(peanut_ingredient, through_defaults=THROUGH_DEFAULTS)
        MealPlanFactory(kitchen=kitchen, meal=meal, service_date=frozen_today)

        card = get_today_card(member)
        assert any(a.name == "Peanut" for a in card["allergens"])

    def test_query_count_bounded(
        self, django_assert_max_num_queries, frozen_today
    ):
        from apps.dashboards.services.member_today import get_today_card

        member = UserFactory(role="member")
        UserAddressFactory(user=member, latitude=-37.82, longitude=144.97)
        kitchen = KitchenFactory(latitude=-37.81, longitude=144.96)
        meal = MealFactory()
        MealPlanFactory(kitchen=kitchen, meal=meal, service_date=frozen_today)
        with django_assert_max_num_queries(8):
            get_today_card(member)

    def test_no_address_returns_empty_state(self, frozen_today):
        """A member without any address can't be matched to a kitchen.

        The view must not 500 — the empty state covers it.
        """
        from apps.dashboards.services.member_today import get_today_card

        member = UserFactory(role="member")
        card = get_today_card(member)
        assert card["has_meal"] is False
        assert card["next_plan_date"] is None

    def test_no_plan_today_returns_next_plan_date(self, frozen_today):
        """If today has no plan but a future plan exists, surface its date."""
        from apps.dashboards.services.member_today import get_today_card

        kitchen = KitchenFactory(latitude=-37.81, longitude=144.96)
        member = UserFactory(role="member")
        UserAddressFactory(user=member, latitude=-37.82, longitude=144.97)
        MealPlanFactory(kitchen=kitchen, service_date=dt.date(2026, 6, 18))

        card = get_today_card(member)
        assert card["has_meal"] is False
        assert card["next_plan_date"] == dt.date(2026, 6, 18)
