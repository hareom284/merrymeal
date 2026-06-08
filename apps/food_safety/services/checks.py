from decimal import Decimal

from django.db.models import QuerySet
from django.utils import timezone

from apps.food_safety.models import FoodSafetyCheck

# Result thresholds for temperature-typed checks.
# (low_inclusive, high_inclusive) — PASS if any inclusive band matches.
THRESHOLDS: dict[str, list[tuple[Decimal | None, Decimal | None]]] = {
    "storage_temp": [(None, Decimal("5.0")), (Decimal("60.0"), None)],
    "cooking_temp": [(Decimal("75.0"), None)],
    "cold_chain":   [(None, Decimal("5.0"))],
}


def derive_result(check_type: str, temperature_celsius: Decimal) -> str:
    bands = THRESHOLDS.get(check_type)
    if bands is None:
        raise ValueError(f"derive_result not defined for {check_type!r}")
    for low, high in bands:
        if (low is None or temperature_celsius >= low) and \
           (high is None or temperature_celsius <= high):
            return FoodSafetyCheck.Result.PASS
    return FoodSafetyCheck.Result.FAIL


def record_check(*, kitchen, user, check_type: str,
                 temperature_celsius: Decimal | None,
                 result: str | None,
                 notes: str) -> FoodSafetyCheck:
    """Write one food-safety check. Server owns checked_at and derives result
    for temperature types."""
    if check_type in THRESHOLDS:
        if temperature_celsius is None:
            raise ValueError("temperature_celsius required for temp check")
        result = derive_result(check_type, temperature_celsius)
    else:
        if result not in {"pass", "fail"}:
            raise ValueError("result required for non-temp check")
        temperature_celsius = None

    return FoodSafetyCheck.objects.create(
        kitchen=kitchen,
        check_type=check_type,
        temperature_celsius=temperature_celsius,
        result=result,
        checked_by=user,
        checked_at=timezone.now(),
        notes=notes or "",
    )


def today_checks_for(user) -> QuerySet[FoodSafetyCheck]:
    today = timezone.localdate()
    return (
        FoodSafetyCheck.objects
        .filter(checked_by=user, checked_at__date=today)
        .order_by("checked_at")
    )
