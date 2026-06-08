import logging

from django.apps import AppConfig

logger = logging.getLogger("merrymeal.donations")


class DonationsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.donations"
    label = "donations"

    def ready(self):
        """Register the donations models with django-auditlog.

        Donations are financial — every status change must be auditable for
        compliance (chargebacks, refunds, tax-receipt reconciliation). Campaign
        edits are also audited because the goal/end-date moves the public
        progress bar and we want a paper trail.

        Mirrors the pattern in ``apps.delivery.apps.DeliveryConfig.ready``:
        the import is side-effect-free at startup (no DB writes) so it does
        not need the OperationalError guard used for django_q schedules.
        """
        try:
            from auditlog.registry import auditlog

            from apps.donations.models import Campaign

            if not auditlog.contains(Campaign):
                auditlog.register(
                    Campaign,
                    include_fields=[
                        "name",
                        "goal_cents",
                        "start_at",
                        "end_at",
                        "is_active",
                        "partner_id",
                    ],
                )

            # ``Donation`` lands in Story 5.2. Import is guarded so the app
            # ``ready()`` hook works through both stories without churn.
            try:
                from apps.donations.models import Donation
            except ImportError:
                Donation = None  # noqa: N806

            if Donation is not None and not auditlog.contains(Donation):
                auditlog.register(
                    Donation,
                    include_fields=[
                        "status",
                        "amount_cents",
                        "transaction_id",
                        "stripe_subscription_id",
                        "receipt_number",
                    ],
                )
        except Exception:  # noqa: BLE001
            logger.exception("Failed to register donations models with auditlog.")
