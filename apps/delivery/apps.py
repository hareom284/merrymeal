import logging

from django.apps import AppConfig
from django.db.utils import OperationalError, ProgrammingError

logger = logging.getLogger("merrymeal.dispatch")


class DeliveryConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.delivery"
    label = "delivery"

    def ready(self):
        """Register the nightly dispatch schedule with Django-Q2 and
        register ``Delivery`` with django-auditlog (Story 4.9).

        `update_or_create` keeps the call idempotent across deploys.
        Wrapped in a broad try/except because `ready()` runs even when
        the django_q tables haven't been migrated yet (fresh install,
        `manage.py migrate` on an empty DB, test bootstrap, etc.).
        """
        # auditlog registration is import-only and side-effect-free at
        # ready() time (no DB writes) so we do it outside the django_q
        # try-block — wrapping it in OperationalError would mask import
        # bugs in the registry module itself.
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
                    ],
                )
        except Exception:  # noqa: BLE001
            logger.exception("Failed to register Delivery with auditlog.")

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
        except (OperationalError, ProgrammingError, ImportError):
            # django_q tables don't exist yet (initial migrate / test
            # bootstrap) or the package isn't importable. Safe to skip.
            logger.debug(
                "django_q tables not ready; skipping dispatch schedule registration."
            )
        except Exception:  # noqa: BLE001
            logger.exception("Failed to register dispatch schedule.")
