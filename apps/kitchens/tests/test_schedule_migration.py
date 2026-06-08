import pytest
from django_q.models import Schedule

pytestmark = pytest.mark.django_db


def test_schedule_row_exists_for_expiry_alerts():
    schedule = Schedule.objects.get(
        func="apps.kitchens.tasks.expiry_alerts.send_expiry_alerts",
    )
    assert schedule.schedule_type == Schedule.CRON
    assert schedule.cron == "0 6 * * *"
    assert schedule.name == "expiry-alerts-daily-06"
