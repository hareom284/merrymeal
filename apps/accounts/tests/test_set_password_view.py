"""End-to-end tests for the `/accounts/set-password/` screen.

Covers the email-link flow:
  1. GET with a valid token renders the form.
  2. GET with a missing/tampered/expired/used token renders the
     friendly error page (HTTP 400) and does NOT consume the token.
  3. POST happy path sets the password, logs the user in, and
     redirects to ``/``.
  4. POST mismatching passwords re-renders the form with errors and
     leaves the token unused.
"""
import pytest
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import PasswordSetupToken
from apps.accounts.services.tokens import (
    consume_password_setup_token,
    issue_password_setup_token,
)
from apps.accounts.tests.factories import UserFactory

pytestmark = pytest.mark.django_db


def _url(token=None):
    base = reverse("accounts:set_password")
    return f"{base}?token={token}" if token else base


def test_get_with_valid_token_renders_form(client):
    user = UserFactory()
    token = issue_password_setup_token(user)
    response = client.get(_url(token))
    assert response.status_code == 200
    assert b"Set your password" in response.content
    assert f'value="{token}"'.encode() in response.content
    # GET must not consume the token.
    assert PasswordSetupToken.objects.get(user=user).used_at is None


def test_get_without_token_returns_friendly_error(client):
    response = client.get(_url())
    assert response.status_code == 400
    assert b"Invalid link" in response.content or b"couldn" in response.content


def test_get_with_tampered_token_returns_friendly_error(client):
    response = client.get(_url("this-is-not-a-valid-signed-token"))
    assert response.status_code == 400
    assert b"Invalid link" in response.content


def test_get_with_used_token_returns_friendly_error(client):
    user = UserFactory()
    token = issue_password_setup_token(user)
    consume_password_setup_token(token)
    response = client.get(_url(token))
    assert response.status_code == 400
    assert b"Already used" in response.content


def test_get_with_expired_db_row_returns_friendly_error(client):
    user = UserFactory()
    token = issue_password_setup_token(user)
    PasswordSetupToken.objects.filter(user=user).update(
        expires_at=timezone.now() - timezone.timedelta(seconds=1)
    )
    response = client.get(_url(token))
    assert response.status_code == 400
    assert b"expired" in response.content.lower()


def test_post_happy_path_sets_password_logs_in_redirects(client):
    user = UserFactory()
    token = issue_password_setup_token(user)
    new_pw = "S3cure-fresh-pass!"
    response = client.post(
        _url(),
        {"token": token, "password1": new_pw, "password2": new_pw},
    )
    assert response.status_code == 302
    assert response["Location"] == "/"

    user.refresh_from_db()
    assert user.check_password(new_pw)
    assert PasswordSetupToken.objects.get(user=user).used_at is not None
    # Logged in via session.
    assert int(client.session["_auth_user_id"]) == user.pk


def test_post_mismatched_passwords_re_renders_form_and_keeps_token(client):
    user = UserFactory()
    token = issue_password_setup_token(user)
    response = client.post(
        _url(),
        {
            "token": token,
            "password1": "S3cure-fresh-pass!",
            "password2": "Different-pass!!",
        },
    )
    assert response.status_code == 200
    assert b"Passwords don" in response.content
    assert PasswordSetupToken.objects.get(user=user).used_at is None
    # Old password (from factory) still works.
    user.refresh_from_db()
    assert user.check_password("pw12345!")


def test_post_weak_password_re_renders_form_and_keeps_token(client):
    user = UserFactory()
    token = issue_password_setup_token(user)
    response = client.post(
        _url(),
        {"token": token, "password1": "1234", "password2": "1234"},
    )
    assert response.status_code == 200
    assert PasswordSetupToken.objects.get(user=user).used_at is None
