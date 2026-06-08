from datetime import timedelta
from decimal import Decimal

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.accounts.tests.factories import UserFactory


pytestmark = pytest.mark.django_db


def _kitchen(name="Footscray"):
    from apps.kitchens.tests.factories import KitchenFactory
    return KitchenFactory(name=name)


def _ingredient():
    from apps.kitchens.tests.factories import IngredientFactory
    return IngredientFactory()


def _batch(*, kitchen, days_to_expiry: int, quantity="1.00"):
    from apps.kitchens.tests.factories import IngredientBatchFactory
    return IngredientBatchFactory(
        kitchen=kitchen,
        ingredient=_ingredient(),
        expiration_date=timezone.localdate() + timedelta(days=days_to_expiry),
        quantity=Decimal(quantity),
    )


def _check(*, kitchen, result, hours_ago=1, check_type="hygiene", checker=None):
    from apps.food_safety.models import FoodSafetyCheck
    return FoodSafetyCheck.objects.create(
        kitchen=kitchen,
        check_type=check_type,
        result=result,
        checked_by=checker or UserFactory(role="kitchen_staff"),
        checked_at=timezone.now() - timedelta(hours=hours_ago),
    )


# ---------- service: expiring count ----------

def test_summary_counts_only_expiring_within_3_days():
    from apps.dashboards.services.kitchen_summary import get_summary
    kitchen = _kitchen()
    _batch(kitchen=kitchen, days_to_expiry=2)
    _batch(kitchen=kitchen, days_to_expiry=5)  # out of window
    summary = get_summary(kitchen)
    assert summary["expiring_count"] == 1


def test_summary_expiring_traffic_light_green_when_zero():
    from apps.dashboards.services.kitchen_summary import get_summary
    kitchen = _kitchen()
    summary = get_summary(kitchen)
    assert summary["expiring_count"] == 0
    assert summary["expiring_status"] == "green"


def test_summary_expiring_traffic_light_yellow_when_some():
    from apps.dashboards.services.kitchen_summary import get_summary
    kitchen = _kitchen()
    for _ in range(3):
        _batch(kitchen=kitchen, days_to_expiry=2)
    summary = get_summary(kitchen)
    assert summary["expiring_status"] == "yellow"


def test_summary_expiring_traffic_light_red_when_above_threshold():
    from apps.dashboards.services.kitchen_summary import get_summary
    kitchen = _kitchen()
    for _ in range(6):  # default red threshold = 5
        _batch(kitchen=kitchen, days_to_expiry=2)
    summary = get_summary(kitchen)
    assert summary["expiring_status"] == "red"


# ---------- service: pass-rate ----------

def test_summary_pass_rate_none_when_no_checks_in_window():
    from apps.dashboards.services.kitchen_summary import get_summary
    kitchen = _kitchen()
    summary = get_summary(kitchen)
    assert summary["pass_rate"] is None
    assert summary["pass_rate_status"] == "grey"


def test_summary_pass_rate_100_when_all_pass():
    from apps.dashboards.services.kitchen_summary import get_summary
    kitchen = _kitchen()
    for _ in range(3):
        _check(kitchen=kitchen, result="pass", hours_ago=1)
    summary = get_summary(kitchen)
    assert summary["pass_rate"] == 100.0
    assert summary["pass_rate_status"] == "green"


def test_summary_pass_rate_yellow_band():
    from apps.dashboards.services.kitchen_summary import get_summary
    kitchen = _kitchen()
    _check(kitchen=kitchen, result="pass", hours_ago=1)
    _check(kitchen=kitchen, result="pass", hours_ago=2)
    _check(kitchen=kitchen, result="pass", hours_ago=3)
    _check(kitchen=kitchen, result="pass", hours_ago=4)
    _check(kitchen=kitchen, result="pass", hours_ago=5)
    _check(kitchen=kitchen, result="pass", hours_ago=6)
    _check(kitchen=kitchen, result="pass", hours_ago=7)
    _check(kitchen=kitchen, result="pass", hours_ago=8)
    _check(kitchen=kitchen, result="pass", hours_ago=9)
    _check(kitchen=kitchen, result="fail", hours_ago=10)  # 9/10 = 90.0
    summary = get_summary(kitchen)
    assert summary["pass_rate"] == 90.0
    assert summary["pass_rate_status"] == "yellow"


def test_summary_pass_rate_red_when_below_yellow_min():
    from apps.dashboards.services.kitchen_summary import get_summary
    kitchen = _kitchen()
    _check(kitchen=kitchen, result="pass", hours_ago=1)
    _check(kitchen=kitchen, result="fail", hours_ago=2)
    summary = get_summary(kitchen)
    assert summary["pass_rate"] == 50.0
    assert summary["pass_rate_status"] == "red"


def test_summary_pass_rate_window_is_24h_only():
    from apps.dashboards.services.kitchen_summary import get_summary
    kitchen = _kitchen()
    _check(kitchen=kitchen, result="pass", hours_ago=1)
    _check(kitchen=kitchen, result="fail", hours_ago=48)  # outside window
    summary = get_summary(kitchen)
    assert summary["pass_rate"] == 100.0


# ---------- service: last failure ----------

def test_summary_no_last_failure_when_none():
    from apps.dashboards.services.kitchen_summary import get_summary
    kitchen = _kitchen()
    summary = get_summary(kitchen)
    assert summary["last_failure"] is None
    assert summary["last_failure_status"] == "green"


def test_summary_last_failure_red_when_within_24h():
    from apps.dashboards.services.kitchen_summary import get_summary
    kitchen = _kitchen()
    _check(kitchen=kitchen, result="fail", hours_ago=2)
    summary = get_summary(kitchen)
    assert summary["last_failure"] is not None
    assert summary["last_failure_status"] == "red"


def test_summary_last_failure_yellow_when_within_7_days():
    from apps.dashboards.services.kitchen_summary import get_summary
    kitchen = _kitchen()
    _check(kitchen=kitchen, result="fail", hours_ago=3 * 24)
    summary = get_summary(kitchen)
    assert summary["last_failure_status"] == "yellow"


def test_summary_last_failure_green_when_older_than_7_days():
    from apps.dashboards.services.kitchen_summary import get_summary
    kitchen = _kitchen()
    _check(kitchen=kitchen, result="fail", hours_ago=10 * 24)
    summary = get_summary(kitchen)
    assert summary["last_failure_status"] == "green"


# ---------- view: access control ----------

def test_anonymous_redirected_to_login(client):
    response = client.get(reverse("dashboards:admin_kitchens"))
    assert response.status_code == 302
    assert "/accounts/login" in response.url


def test_non_admin_gets_403(client):
    client.force_login(UserFactory(role="kitchen_staff"))
    response = client.get(reverse("dashboards:admin_kitchens"))
    assert response.status_code == 403


def test_admin_sees_one_card_per_kitchen(client):
    client.force_login(UserFactory(role="admin"))
    _kitchen("Footscray")
    _kitchen("St Kilda")
    response = client.get(reverse("dashboards:admin_kitchens"))
    assert response.status_code == 200
    assert b"Footscray" in response.content
    assert b"St Kilda" in response.content


def test_admin_sees_empty_state_when_no_kitchens(client):
    client.force_login(UserFactory(role="admin"))
    response = client.get(reverse("dashboards:admin_kitchens"))
    assert response.status_code == 200
    assert b"No kitchens registered yet" in response.content


def test_cards_link_to_filtered_lists(client):
    client.force_login(UserFactory(role="admin"))
    kitchen = _kitchen("Footscray")
    _batch(kitchen=kitchen, days_to_expiry=1)
    response = client.get(reverse("dashboards:admin_kitchens"))
    body = response.content.decode()
    assert "kitchen" in body.lower()
    assert str(kitchen.id) in body


# ---------- query count guard ----------

def test_query_count_stays_linear_in_n_kitchens(client, django_assert_max_num_queries):
    client.force_login(UserFactory(role="admin"))
    for i in range(3):
        _kitchen(name=f"K{i}")

    # 4 queries per kitchen (expiring, total checks, passed checks, last failure)
    # + outer Kitchen list + auth session lookups (allow 8 for overhead).
    with django_assert_max_num_queries(4 * 3 + 8):
        client.get(reverse("dashboards:admin_kitchens"))
