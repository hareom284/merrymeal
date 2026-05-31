import pytest
from django.contrib.auth.models import AnonymousUser
from django.http import HttpResponse
from django.test import RequestFactory

from apps.core.decorators import role_required


@role_required("admin")
def _admin_view(request):
    return HttpResponse("ok")


@pytest.mark.django_db
def test_anonymous_user_is_redirected_to_login():
    request = RequestFactory().get("/x")
    request.user = AnonymousUser()
    response = _admin_view(request)
    assert response.status_code == 302
    assert "/accounts/login/" in response.url


@pytest.mark.django_db
def test_wrong_role_returns_403(django_user_model):
    user = django_user_model.objects.create_user(
        email="m@example.com", password="x", role="member", full_name="M"
    )
    request = RequestFactory().get("/x")
    request.user = user
    response = _admin_view(request)
    assert response.status_code == 403


@pytest.mark.django_db
def test_correct_role_allows_through(django_user_model):
    user = django_user_model.objects.create_user(
        email="a@example.com", password="x", role="admin", full_name="A"
    )
    request = RequestFactory().get("/x")
    request.user = user
    response = _admin_view(request)
    assert response.status_code == 200
