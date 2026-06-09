from django.db import transaction

from apps.accounts.models import User
from apps.core.services import soft_delete


def create_user(*, email: str, password: str, full_name: str, role: str, **extra) -> User:
    """Create a user with the given role. Preferred entry point for
    app code (views, other services, tests, fixtures).
    """
    return User.objects.create_user(
        email=email, password=password, full_name=full_name, role=role, **extra
    )


def delete_user(user: User) -> None:
    """Soft-delete a user (sets deleted_at; row is preserved for audit)."""
    soft_delete(user)


def deactivate_user(target: User, admin_user: User) -> None:
    """Flip ``is_active`` off so the user can't sign in and their
    record is excluded from active-only lists. Wrapped in an
    audit-logged transaction so the admin who deactivated is recorded
    against the LogEntry.

    Idempotent — calling on an already-inactive user is a no-op.
    Used for both members (Story 12.11) and volunteers (Story 12.13);
    the function is role-agnostic.
    """
    from auditlog.context import set_actor

    if not target.is_active:
        return
    with set_actor(admin_user), transaction.atomic():
        target.is_active = False
        target.save(update_fields=["is_active", "updated_at"])


def reactivate_user(target: User, admin_user: User) -> None:
    """Counterpart to :func:`deactivate_user` — flips ``is_active`` on."""
    from auditlog.context import set_actor

    if target.is_active:
        return
    with set_actor(admin_user), transaction.atomic():
        target.is_active = True
        target.save(update_fields=["is_active", "updated_at"])


# Backwards-compatible aliases used by the members CRUD (Story 12.11).
# The function body is identical — kept as named exports so callers
# read clearly at the call site.
deactivate_member = deactivate_user
reactivate_member = reactivate_user
