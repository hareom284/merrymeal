import pytest
from django.contrib.auth.middleware import AuthenticationMiddleware
from django.contrib.sessions.middleware import SessionMiddleware
from django.test import RequestFactory

from apps.accounts.services import sign_in, sign_out
from apps.accounts.tests.factories import UserFactory


def _request_with_session():
    request = RequestFactory().post("/login/")
    SessionMiddleware(lambda r: None).process_request(request)
    AuthenticationMiddleware(lambda r: None).process_request(request)
    return request


@pytest.mark.django_db
def test_sign_in_returns_user_on_success():
    UserFactory(email="alice@example.com", password="pw12345!")
    request = _request_with_session()
    user = sign_in(request, email="alice@example.com", password="pw12345!")
    assert user is not None
    assert user.email == "alice@example.com"


@pytest.mark.django_db
def test_sign_in_returns_none_on_wrong_password():
    UserFactory(email="alice@example.com", password="pw12345!")
    request = _request_with_session()
    user = sign_in(request, email="alice@example.com", password="wrong")
    assert user is None


@pytest.mark.django_db
def test_sign_in_returns_none_for_unknown_user():
    request = _request_with_session()
    user = sign_in(request, email="ghost@example.com", password="x")
    assert user is None


@pytest.mark.django_db
def test_sign_out_clears_session():
    user = UserFactory(email="alice@example.com", password="pw12345!")
    request = _request_with_session()
    sign_in(request, email="alice@example.com", password="pw12345!")
    assert request.session.get("_auth_user_id") == str(user.pk)
    sign_out(request)
    assert "_auth_user_id" not in request.session
