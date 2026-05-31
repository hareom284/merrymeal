from django.contrib.auth import authenticate, login, logout
from django.http import HttpRequest

from apps.accounts.models import User


def sign_in(request: HttpRequest, *, email: str, password: str) -> User | None:
    """Authenticate credentials, start a session, return the user (or None)."""
    user = authenticate(request, email=email, password=password)
    if user is None:
        return None
    login(request, user)
    return user


def sign_out(request: HttpRequest) -> None:
    """End the current session."""
    logout(request)
