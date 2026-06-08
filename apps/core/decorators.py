from functools import wraps

from django.http import HttpResponseForbidden
from django.shortcuts import redirect
from django.urls import reverse


def role_required(*roles: str):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            user = request.user
            if not user.is_authenticated:
                return redirect(reverse("accounts:login"))
            if getattr(user, "role", None) not in roles:
                return HttpResponseForbidden("Forbidden")
            return view_func(request, *args, **kwargs)

        return _wrapped

    return decorator


def partner_required(view_func):
    """Gate a view on the requester being linked to a partner organisation.

    The ``users.role`` enum in this codebase does not include a
    dedicated ``"partner"`` role — partner staff are represented by
    existing roles (typically ``admin`` or ``kitchen_staff``) with a
    non-NULL ``partner_id`` FK. The single source of truth for partner
    identity is therefore ``request.user.partner_id``; this decorator
    short-circuits with HTTP 403 when that column is NULL and explains
    why so the user can contact a MerryMeal admin to fix the link.

    Anonymous users are redirected to login (matching
    :func:`role_required`).
    """

    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        user = request.user
        if not user.is_authenticated:
            return redirect(reverse("accounts:login"))
        if getattr(user, "partner_id", None) is None:
            return HttpResponseForbidden(
                "Your account is not linked to a partner organisation. "
                "Contact MerryMeal admin to fix this."
            )
        return view_func(request, *args, **kwargs)

    return _wrapped
