import pytest
from django.urls import reverse

from apps.accounts.tests.factories import UserFactory


@pytest.mark.django_db
def test_login_page_renders(client):
    response = client.get(reverse("accounts:login"))
    assert response.status_code == 200
    assert b"Sign in" in response.content


@pytest.mark.django_db
def test_login_succeeds_with_correct_credentials(client):
    UserFactory(email="a@example.com", password="pw12345!")
    response = client.post(
        reverse("accounts:login"),
        {"email": "a@example.com", "password": "pw12345!"},
    )
    assert response.status_code == 302


@pytest.mark.django_db
def test_login_fails_with_wrong_password(client):
    UserFactory(email="a@example.com", password="pw12345!")
    response = client.post(
        reverse("accounts:login"),
        {"email": "a@example.com", "password": "wrong"},
    )
    assert response.status_code == 200
    assert b"Invalid" in response.content


@pytest.mark.django_db
def test_logout_redirects_to_login(client):
    user = UserFactory()
    client.force_login(user)
    response = client.post(reverse("accounts:logout"))
    assert response.status_code == 302
    assert reverse("accounts:login") in response.url
