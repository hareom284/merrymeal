import logging

from django.apps import AppConfig

logger = logging.getLogger("merrymeal.accounts")


class AccountsConfig(AppConfig):
    name = "apps.accounts"
    label = "accounts"

    def ready(self):
        """Register ``User`` and ``Application`` with django-auditlog.

        Story 6.6's audit viewer reads ``auditlog.LogEntry`` and surfaces
        member-approval history (who approved/rejected which application,
        when). The approve/reject services in
        ``apps.accounts.services.applications`` already wrap their DB
        writes in ``auditlog.context.set_actor(admin_user)``, but
        ``LogEntry`` rows only get written for models that have been
        registered with the registry. Without the registration below the
        viewer returns an empty result.

        Mirrors the pattern in ``apps.donations.apps.DonationsConfig.ready``:
        the imports are side-effect-free at startup (no DB writes), so we
        don't need the OperationalError guard used for django_q schedules.

        Fields excluded from each model:

        * ``User.password`` — credential hash, never goes near an audit
          log. ``User.last_login`` and ``User.updated_at`` are noisy
          (fire on every sign-in / every save) and aren't useful for the
          approval-trail story.
        * ``Application.dietary_ids``, ``allergy_ids``, ``metadata`` are
          JSON blobs that change shape over time and would balloon every
          LogEntry's ``changes`` payload without aiding the
          approve/reject paper trail. ``updated_at`` is excluded for the
          same reason as on User.
        """
        try:
            from auditlog.registry import auditlog

            from apps.accounts.models import Application, User

            if not auditlog.contains(User):
                auditlog.register(
                    User,
                    exclude_fields=[
                        "password",
                        "last_login",
                        "updated_at",
                    ],
                )

            if not auditlog.contains(Application):
                auditlog.register(
                    Application,
                    exclude_fields=[
                        "dietary_ids",
                        "allergy_ids",
                        "metadata",
                        "updated_at",
                    ],
                )
        except Exception:  # noqa: BLE001
            logger.exception("Failed to register accounts models with auditlog.")
