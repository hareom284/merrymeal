from decimal import Decimal

import factory
from django.utils import timezone

from apps.food_safety.models import FoodSafetyCheck


class FoodSafetyCheckFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = FoodSafetyCheck

    # kitchen and checked_by are always passed by the caller to avoid circular imports
    check_type = FoodSafetyCheck.CheckType.STORAGE_TEMP
    temperature_celsius = Decimal("4.00")
    result = FoodSafetyCheck.Result.PASS
    checked_at = factory.LazyFunction(timezone.now)
    notes = ""
