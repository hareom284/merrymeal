import pytest
from django.core import mail
from django.urls import reverse

from apps.accounts.tests.factories import UserFactory


@pytest.mark.django_db
def test_password_reset_form_renders(client):
    response = client.get(reverse("accounts:password_reset"))
    assert response.status_code == 200
    assert b"Reset password" in response.content


@pytest.mark.django_db
def test_password_reset_sends_email(client):
    UserFactory(email="reset@example.com")
    response = client.post(
        reverse("accounts:password_reset"),
        {"email": "reset@example.com"},
    )
    assert response.status_code == 302
    assert len(mail.outbox) == 1
    assert "reset@example.com" in mail.outbox[0].to
