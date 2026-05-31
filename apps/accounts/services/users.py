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
