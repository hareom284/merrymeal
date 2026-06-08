from django.core.management.base import BaseCommand
from django.db import transaction

from apps.accounts.models import CaregiverLink, User
from apps.partners.models import Partner

PASSWORD = "testpass123"
EMAIL_DOMAIN = "test.merrymeal.local"

# Roles seeded by this command. Admin is intentionally excluded — that user
# is owned by `seed_admin` and reads its email/password from a separate set
# of env vars.
SEED_USERS = [
    {"role": "member", "full_name": "Test Member"},
    {"role": "volunteer", "full_name": "Test Volunteer"},
    {"role": "caregiver", "full_name": "Test Caregiver"},
    {"role": "donor", "full_name": "Test Donor"},
    {"role": "kitchen_staff", "full_name": "Test Kitchen Staff"},
]

# Partner-affiliated user. The User model has no ``partner`` role; partner
# access is granted by setting ``user.partner`` to a Partner row (see the
# spec-vs-codebase substitution catalog in CLAUDE.md).
PARTNER_USER = {"role": "member", "full_name": "Test Partner User"}
PARTNER_LEGAL_NAME = "Test Partner Charity"


class Command(BaseCommand):
    help = (
        "Create one test user per role for local QA. Idempotent — safe to "
        "re-run. Every user is created with the hard-coded password "
        f"{PASSWORD!r}. Emails are <role>@test.merrymeal.local. Also "
        "creates a partner-affiliated member and a CaregiverLink from the "
        "caregiver to the member so the caregiver dashboard has content."
    )

    def handle(self, *args, **options):
        password = PASSWORD

        with transaction.atomic():
            created = []
            for spec in SEED_USERS:
                user, verb = self._upsert_user(
                    email=f"{spec['role']}@{EMAIL_DOMAIN}",
                    role=spec["role"],
                    full_name=spec["full_name"],
                    password=password,
                )
                created.append((verb, user))

            partner, partner_verb = self._upsert_partner()
            partner_user, partner_user_verb = self._upsert_user(
                email=f"partner@{EMAIL_DOMAIN}",
                role=PARTNER_USER["role"],
                full_name=PARTNER_USER["full_name"],
                password=password,
                partner=partner,
            )
            created.append((partner_user_verb, partner_user))

            member = next(u for v, u in created if u.role == "member" and u.partner_id is None)
            caregiver = next(u for v, u in created if u.role == "caregiver")
            link, link_created = CaregiverLink.objects.get_or_create(
                member=member,
                caregiver=caregiver,
                defaults={"relationship": "family"},
            )

        self.stdout.write(self.style.SUCCESS("seed_test_users:"))
        self.stdout.write(
            f"  partner: {partner_verb} {partner.legal_name} (id={partner.id})"
        )
        for verb, u in created:
            partner_tag = f" partner={u.partner.legal_name!r}" if u.partner_id else ""
            self.stdout.write(
                f"  user: {verb} {u.email} role={u.role}{partner_tag}"
            )
        self.stdout.write(
            f"  caregiver link: {'created' if link_created else 'exists'} "
            f"({caregiver.email} → {member.email})"
        )
        self.stdout.write("")
        self.stdout.write(self.style.WARNING(f"  shared password: {password}"))

    def _upsert_user(self, *, email, role, full_name, password, partner=None):
        email = email.strip().lower()
        existing = User.all_objects.filter(email=email).first()
        if existing is None:
            user = User.objects.create_user(
                email=email,
                password=password,
                full_name=full_name,
                role=role,
            )
            if partner is not None:
                user.partner = partner
                user.save(update_fields=["partner", "updated_at"])
            return user, "created"

        existing.full_name = full_name
        existing.role = role
        existing.is_active = True
        existing.deleted_at = None
        existing.partner = partner
        existing.set_password(password)
        existing.save()
        return existing, "updated"

    def _upsert_partner(self):
        existing = Partner.objects.filter(legal_name=PARTNER_LEGAL_NAME).first()
        if existing is None:
            partner = Partner.objects.create(
                legal_name=PARTNER_LEGAL_NAME,
                type="charity",
            )
            return partner, "created"
        return existing, "exists"
