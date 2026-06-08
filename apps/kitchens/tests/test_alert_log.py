from django.utils import timezone

import pytest
from django.db import IntegrityError

from apps.kitchens.models import ExpiryAlertLog
from apps.kitchens.tests.factories import KitchenFactory


pytestmark = pytest.mark.django_db(transaction=True)


def test_unique_kitchen_per_day():
    kitchen = KitchenFactory()
    today = timezone.localdate()
    ExpiryAlertLog.objects.create(kitchen=kitchen, sent_date=today)
    with pytest.raises(IntegrityError):
        ExpiryAlertLog.objects.create(kitchen=kitchen, sent_date=today)
