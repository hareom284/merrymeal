"""Register the nightly Django-Q2 schedule for
``apps.planning.tasks.validate.run_nightly_validation``.

Pattern lifted from
``apps/kitchens/migrations/0006_schedule_expiry_alerts.py``. Keeps
schedule state in the DB rather than an ``AppConfig.ready()`` hook so
``makemigrations`` on a fresh DB never trips over a missing
``django_q_schedule`` table.
"""

from django.db import migrations

TASK_FUNC = "apps.planning.tasks.validate.run_nightly_validation"


def create_schedule(apps, schema_editor):
    Schedule = apps.get_model("django_q", "Schedule")
    # Cron: 02:30 every day (Australia/Melbourne — django-q uses
    # settings.TIME_ZONE). Runs after the 06:00 expiry-alerts job's
    # window so the two don't pile up on the same minute.
    Schedule.objects.update_or_create(
        func=TASK_FUNC,
        defaults={
            "name": "validate-radius-daily-0230",
            "schedule_type": "C",
            "cron": "30 2 * * *",
            "repeats": -1,
        },
    )


def remove_schedule(apps, schema_editor):
    Schedule = apps.get_model("django_q", "Schedule")
    Schedule.objects.filter(func=TASK_FUNC).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("planning", "0001_initial"),
        ("django_q", "0019_alter_task_options_alter_ormq_key_alter_ormq_lock_and_more"),
    ]
    operations = [
        migrations.RunPython(create_schedule, remove_schedule),
    ]
