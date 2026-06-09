"""Tests for the standalone weekly menu page (Story 12.5).

The page reuses the dashboard's week-menu data but gives each day a
richer card (ingredients, allergens, kitchen, delivery state). Mounted
at ``/menu/`` and reachable from the Menu bottom-nav tab plus the
dashboard's ``See full week`` CTA.
"""
import datetime as dt

import pytest

from apps.accounts.tests.factories import AddressFactory, CityFactory, UserFactory
from apps.dashboards.services.weekly_menu import build_weekly_menu_context
from apps.dietary.models import Allergy, UserAllergy
from apps.kitchens.models import Kitchen
from apps.kitchens.tests.factories import KitchenFactory
from apps.meals.tests.factories import MealFactory
from apps.planning.models import MealPlan
from apps.planning.tests.factories import MealPlanFactory


def _make_plan(date: dt.date, meal_name: str, kitchen: Kitchen) -> MealPlan:
    meal = MealFactory(name=meal_name)
    return MealPlanFactory(meal=meal, kitchen=kitchen, service_date=date)


@pytest.fixture
def member_with_city(db):
    """A member with an address that has lat/lng — required for the
    nearest-kitchen lookup to consider any MealPlan."""
    from decimal import Decimal
    city = CityFactory(name="Melbourne")
    member = UserFactory(role="member")
    AddressFactory(
        user=member,
        city=city,
        latitude=Decimal("-37.8136"),
        longitude=Decimal("144.9631"),
    )
    return member


@pytest.mark.django_db
def test_weekly_menu_requires_login(client):
    response = client.get("/menu/")
    assert response.status_code == 302


@pytest.mark.django_db
def test_weekly_menu_renders_for_authenticated_member(client, member_with_city):
    client.force_login(member_with_city)
    response = client.get("/menu/")
    assert response.status_code == 200
    assert b"week" in response.content.lower()


@pytest.mark.django_db
def test_weekly_menu_lists_seven_days(member_with_city):
    """The standalone page shows a full 7-day week (the dashboard strip
    only shows 5 weekdays). All 7 day labels appear in order."""
    context = build_weekly_menu_context(member_with_city, today=dt.date(2026, 6, 10))
    days = context["days"]
    assert [d["weekday"] for d in days] == [
        "MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN",
    ]


@pytest.mark.django_db
def test_weekly_menu_marks_today(member_with_city):
    """Today's card gets ``state=today``; past days get ``done``;
    future days get ``upcoming``."""
    wednesday = dt.date(2026, 6, 10)
    context = build_weekly_menu_context(member_with_city, today=wednesday)
    days = context["days"]
    states = [d["state"] for d in days]
    # MON, TUE are past; WED is today; THU-SUN are upcoming.
    assert states == ["done", "done", "today", "upcoming", "upcoming", "upcoming", "upcoming"]


@pytest.mark.django_db
def test_weekly_menu_picks_meal_per_day(member_with_city):
    """When a MealPlan exists for the day, its meal name surfaces.
    When no plan exists, the card shows an em-dash placeholder."""
    kitchen = KitchenFactory()
    monday = dt.date(2026, 6, 8)
    _make_plan(monday, "Roast chicken", kitchen)
    context = build_weekly_menu_context(member_with_city, today=monday)
    assert context["days"][0]["meal_name"] == "Roast chicken"
    assert context["days"][1]["meal_name"] == "—"


@pytest.mark.django_db
def test_weekly_menu_flags_member_allergens(member_with_city):
    """If a planned meal contains an ingredient the member is allergic
    to, the day card surfaces that allergen so the member sees the
    warning at a glance without opening the meal."""
    from apps.kitchens.models import Ingredient, MealIngredient

    kitchen = KitchenFactory()
    monday = dt.date(2026, 6, 8)
    plan = _make_plan(monday, "Peanut noodles", kitchen)

    peanut = Allergy.objects.create(name="Peanuts")
    UserAllergy.objects.create(user=member_with_city, allergy=peanut)
    ingr = Ingredient.objects.create(name="Peanut sauce", unit="g")
    ingr.contains_allergens.add(peanut)
    MealIngredient.objects.create(meal=plan.meal, ingredient=ingr, quantity=10)

    context = build_weekly_menu_context(member_with_city, today=monday)
    monday_card = context["days"][0]
    assert any(a.name == "Peanuts" for a in monday_card["allergens"])


@pytest.mark.django_db
def test_weekly_menu_view_links_to_help(client, member_with_city):
    """Bottom-nav Help link must still appear on the menu page so the
    member can pivot to support without going back home first."""
    client.force_login(member_with_city)
    response = client.get("/menu/")
    assert b"/help/" in response.content


@pytest.mark.django_db
def test_weekly_menu_no_dead_links(client, member_with_city):
    client.force_login(member_with_city)
    response = client.get("/menu/")
    assert b'href="#"' not in response.content
