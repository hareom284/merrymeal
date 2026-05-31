import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError

from apps.accounts.services import create_user, delete_user

User = get_user_model()


@pytest.mark.django_db
def test_user_schema_basics():
    """Model is schema-only; we exercise it via the service."""
    user = create_user(email="a@example.com", password="pw", full_name="Alice", role="member")
    assert user.email == "a@example.com"
    assert user.full_name == "Alice"
    assert user.role == "member"
    assert user.check_password("pw")
    assert user.is_active is True
    assert user.deleted_at is None


@pytest.mark.django_db
def test_email_is_unique():
    create_user(email="a@example.com", password="pw", full_name="A", role="member")
    with pytest.raises(IntegrityError):
        create_user(email="a@example.com", password="pw", full_name="A2", role="donor")


@pytest.mark.django_db
def test_delete_user_soft_deletes_and_hides_from_default_manager():
    user = create_user(email="a@example.com", password="pw", full_name="A", role="member")
    pk = user.pk
    delete_user(user)
    assert user.deleted_at is not None
    assert User.objects.filter(pk=pk).count() == 0
    assert User.all_objects.filter(pk=pk).count() == 1
