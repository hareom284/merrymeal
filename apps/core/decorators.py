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
