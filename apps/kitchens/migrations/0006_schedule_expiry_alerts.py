from django.db import migrations

TASK_FUNC = "apps.kitchens.tasks.expiry_alerts.send_expiry_alerts"


def create_schedule(apps, schema_editor):
    Schedule = apps.get_model("django_q", "Schedule")
    Schedule.objects.update_or_create(
        func=TASK_FUNC,
        defaults={
            "name": "expiry-alerts-daily-06",
            "schedule_type": "C",
            "cron": "0 6 * * *",
            "repeats": -1,
        },
    )


def remove_schedule(apps, schema_editor):
    Schedule = apps.get_model("django_q", "Schedule")
    Schedule.objects.filter(func=TASK_FUNC).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("kitchens", "0005_expiry_alert_log"),
        ("django_q", "0019_alter_task_options_alter_ormq_key_alter_ormq_lock_and_more"),
    ]
    operations = [
        migrations.RunPython(create_schedule, remove_schedule),
    ]
