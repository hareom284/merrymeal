from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from apps.food_safety.models import FoodSafetyCheck
from apps.kitchens.models import Kitchen
from apps.kitchens.services.expiry import find_expiring_batches


# ---------- thresholds ----------

EXPIRING_WITHIN_DAYS = 3
EXPIRING_RED_THRESHOLD = 5      # > 5 expiring batches = red

PASSRATE_WINDOW_HOURS = 24
PASSRATE_YELLOW_MIN = 90.0      # 90.0 <= rate < 100 = yellow; < 90 = red

FAILURE_RED_HOURS = 24
FAILURE_YELLOW_DAYS = 7


def _override(name: str, default):
    overrides = getattr(settings, "KITCHEN_DASHBOARD_THRESHOLDS", {}) or {}
    return overrides.get(name, default)


# ---------- metric helpers ----------

def _expiring_status(count: int) -> str:
    if count == 0:
        return "green"
    if count <= _override("EXPIRING_RED_THRESHOLD", EXPIRING_RED_THRESHOLD):
        return "yellow"
    return "red"


def _pass_rate_status(rate) -> str:
    if rate is None:
        return "grey"
    if rate >= 100.0:
        return "green"
    if rate >= _override("PASSRATE_YELLOW_MIN", PASSRATE_YELLOW_MIN):
        return "yellow"
    return "red"


def _last_failure_status(failure) -> str:
    if failure is None:
        return "green"
    now = timezone.now()
    age = now - failure.checked_at
    if age <= timedelta(hours=_override("FAILURE_RED_HOURS", FAILURE_RED_HOURS)):
        return "red"
    if age <= timedelta(days=_override("FAILURE_YELLOW_DAYS", FAILURE_YELLOW_DAYS)):
        return "yellow"
    return "green"


# ---------- main ----------

def get_summary(kitchen: Kitchen) -> dict:
    expiring_count = find_expiring_batches(kitchen, within_days=EXPIRING_WITHIN_DAYS).count()

    window_start = timezone.now() - timedelta(hours=PASSRATE_WINDOW_HOURS)
    checks_qs = FoodSafetyCheck.objects.filter(kitchen=kitchen, checked_at__gte=window_start)
    total = checks_qs.count()
    passed = checks_qs.filter(result="pass").count()
    pass_rate = round((passed / total) * 100.0, 2) if total else None

    last_failure = (
        FoodSafetyCheck.objects
        .filter(kitchen=kitchen, result="fail")
        .order_by("-checked_at")
        .first()
    )

    expiring_href = (
        f"/admin/kitchens/ingredientbatch/?kitchen__id__exact={kitchen.id}"
    )
    pass_rate_href = (
        f"/admin/food_safety/foodsafetycheck/?kitchen__id__exact={kitchen.id}"
    )
    last_failure_href = (
        f"/admin/food_safety/foodsafetycheck/{last_failure.id}/change/"
        if last_failure else ""
    )

    return {
        "kitchen": kitchen,
        "expiring_count": expiring_count,
        "expiring_status": _expiring_status(expiring_count),
        "expiring_href": expiring_href,
        "pass_rate": pass_rate,
        "pass_rate_status": _pass_rate_status(pass_rate),
        "pass_rate_href": pass_rate_href,
        "last_failure": last_failure,
        "last_failure_status": _last_failure_status(last_failure),
        "last_failure_href": last_failure_href,
    }
