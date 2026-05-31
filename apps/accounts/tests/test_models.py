import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError

User = get_user_model()


@pytest.mark.django_db
def test_user_requires_email_and_role():
    user = User.objects.create_user(
        email="a@example.com", password="pw", full_name="Alice", role="member"
    )
    assert user.email == "a@example.com"
    assert user.full_name == "Alice"
    assert user.role == "member"
    assert user.check_password("pw")
    assert user.is_active is True
    assert user.deleted_at is None


@pytest.mark.django_db
def test_email_is_unique():
    User.objects.create_user(
        email="a@example.com", password="pw", full_name="A", role="member"
    )
    with pytest.raises(IntegrityError):
        User.objects.create_user(
            email="a@example.com", password="pw", full_name="A2", role="donor"
        )


@pytest.mark.django_db
def test_soft_delete_hides_user_from_default_manager():
    user = User.objects.create_user(
        email="a@example.com", password="pw", full_name="A", role="member"
    )
    pk = user.pk
    user.delete()
    assert User.objects.filter(pk=pk).count() == 0
    assert User.all_objects.filter(pk=pk).count() == 1
