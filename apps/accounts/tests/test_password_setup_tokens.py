import time

import pytest
from django.utils import timezone

from apps.accounts.models import PasswordSetupToken
from apps.accounts.services.tokens import (
    ConsumedTokenError,
    ExpiredTokenError,
    InvalidTokenError,
    consume_password_setup_token,
    issue_password_setup_token,
)
from apps.accounts.tests.factories import UserFactory


pytestmark = pytest.mark.django_db


def test_issue_creates_db_row_and_returns_string():
    user = UserFactory()
    token = issue_password_setup_token(user)
    assert isinstance(token, str)
    row = PasswordSetupToken.objects.get(user=user)
    assert row.used_at is None
    assert row.expires_at > timezone.now()


def test_consume_returns_user_and_marks_used():
    user = UserFactory()
    token = issue_password_setup_token(user)
    returned_user = consume_password_setup_token(token)
    assert returned_user.pk == user.pk
    row = PasswordSetupToken.objects.get(user=user)
    assert row.used_at is not None


def test_consume_twice_raises_consumed_error():
    user = UserFactory()
    token = issue_password_setup_token(user)
    consume_password_setup_token(token)
    with pytest.raises(ConsumedTokenError):
        consume_password_setup_token(token)


def test_consume_tampered_token_raises_invalid_error():
    user = UserFactory()
    issue_password_setup_token(user)
    with pytest.raises(InvalidTokenError):
        consume_password_setup_token("this-is-not-a-valid-signed-token")


def test_consume_expired_db_row_raises_expired_error():
    user = UserFactory()
    token = issue_password_setup_token(user)
    # Fast-expire the DB row
    PasswordSetupToken.objects.filter(user=user).update(
        expires_at=timezone.now() - timezone.timedelta(seconds=1)
    )
    with pytest.raises(ExpiredTokenError):
        consume_password_setup_token(token)
