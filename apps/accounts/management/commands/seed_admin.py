import secrets

from django.core.management.base import BaseCommand
from environ import Env

from apps.accounts.models import User

env = Env()

DEFAULT_ADMIN_EMAIL = "admin@merrymeal.freebarcodeqr.com"
DEFAULT_ADMIN_NAME = "Site Admin"


class Command(BaseCommand):
    help = (
        "Create or update the platform super-admin user. Idempotent. "
        "Reads DJANGO_ADMIN_EMAIL, DJANGO_ADMIN_NAME, DJANGO_ADMIN_PASSWORD from env. "
        "If DJANGO_ADMIN_PASSWORD is unset, a random one is generated on first "
        "create and printed to stdout; on subsequent runs the existing password "
        "is left untouched."
    )

    def handle(self, *args, **options):
        email = env.str("DJANGO_ADMIN_EMAIL", default=DEFAULT_ADMIN_EMAIL).strip().lower()
        full_name = env.str("DJANGO_ADMIN_NAME", default=DEFAULT_ADMIN_NAME)
        env_password = env.str("DJANGO_ADMIN_PASSWORD", default="")

        existing = User.all_objects.filter(email=email).first()

        if existing is None:
            password = env_password or secrets.token_urlsafe(16)
            user = User.objects.create_superuser(
                email=email,
                password=password,
                full_name=full_name,
            )
            verb = "created"
            if not env_password:
                self.stdout.write(
                    self.style.WARNING(
                        f"seed_admin: generated random password for {email}: {password}\n"
                        "  Store this securely — it won't be shown again."
                    )
                )
        else:
            existing.full_name = full_name
            existing.role = "admin"
            existing.is_staff = True
            existing.is_superuser = True
            existing.is_active = True
            existing.deleted_at = None
            if env_password:
                existing.set_password(env_password)
            existing.save()
            user = existing
            verb = "updated"

        self.stdout.write(
            self.style.SUCCESS(f"seed_admin: {verb} {user.email} (id={user.id})")
        )
