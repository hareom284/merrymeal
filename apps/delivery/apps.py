import logging

from django.apps import AppConfig
from django.db.models.signals import post_migrate

logger = logging.getLogger("merrymeal.dispatch")


def _register_dispatch_schedules(sender, **kwargs):
    """Idempotently install the nightly dispatch schedules.

    Wired to ``post_migrate`` (not ``AppConfig.ready``) so the DB
    writes happen only when the django_q tables are known to exist
    and Django's ``Accessing the database during app initialization
    is discouraged`` warning never fires. ``update_or_create`` keeps
    the call idempotent across deploys.
    """
    if sender.name != "apps.delivery":
        return
    try:
        from django_q.models import Schedule

        Schedule.objects.update_or_create(
            name="generate_deliveries_for_today",
            defaults={
                "func": "apps.delivery.tasks.generate_deliveries.run_for_today",
                "schedule_type": Schedule.DAILY,
                # 04:00 Australia/Melbourne (USE_TZ=True, TIME_ZONE
                # already pinned to Australia/Melbourne in settings).
                "cron": "0 4 * * *",
                "repeats": -1,
            },
        )
        Schedule.objects.update_or_create(
            name="assign_routes_for_today",
            defaults={
                "func": "apps.delivery.tasks.assign_routes.run_for_today",
                "schedule_type": Schedule.DAILY,
                # 04:30 Australia/Melbourne — 30 minutes after the
                # generator. The gap absorbs retries on small datasets.
                "cron": "30 4 * * *",
                "repeats": -1,
            },
        )
    except Exception:  # noqa: BLE001
        logger.exception("Failed to register dispatch schedule.")


class DeliveryConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.delivery"
    label = "delivery"

    def ready(self):
        """Register ``Delivery`` with django-auditlog (Story 4.9), wire
        the caregiver-alert signal (Story 4.13), and connect the
        post_migrate handler that installs the dispatch schedule rows.
        """
        from apps.delivery import signals  # noqa: F401

        try:
            from auditlog.registry import auditlog

            from apps.delivery.models import Delivery

            if not auditlog.contains(Delivery):
                auditlog.register(
                    Delivery,
                    include_fields=[
                        "status",
                        "delivered_time",
                        "photo",
                        "latitude",
                        "longitude",
                        # Story 4.10 — record the failure reason so the
                        # admin follow-up screen can reconstruct the
                        # sequence of events for a contested drop-off.
                        "failure_reason",
                    ],
                )
        except Exception:  # noqa: BLE001
            logger.exception("Failed to register Delivery with auditlog.")

        post_migrate.connect(_register_dispatch_schedules, sender=self)
