"""Welcome `set-password/` screen reached from the approval email.

Pairs the link generated in ``apps.accounts.services.applications`` with
the single-use token issued/consumed by ``apps.accounts.services.tokens``.

Flow:
  * GET  /accounts/set-password/?token=<signed>
      - signature ok + DB row unused/unexpired -> render form
      - else                                   -> friendly error page
  * POST same path with token in a hidden form field
      - re-verify, validate password form, consume token, save
        password, session-login, redirect to ``/`` (the landing view
        routes the user to their role's dashboard).
"""
from __future__ import annotations

from django.contrib.auth import login
from django.db import transaction
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from apps.accounts.forms import SetPasswordForm
from apps.accounts.services.tokens import (
    ConsumedTokenError,
    ExpiredTokenError,
    InvalidTokenError,
    consume_password_setup_token,
    verify_password_setup_token,
)

INVALID_TEMPLATE = "accounts/set_password_invalid.html"


def _invalid(request, reason: str):
    return render(request, INVALID_TEMPLATE, {"reason": reason}, status=400)


@require_http_methods(["GET", "POST"])
def set_password_view(request):
    token = request.GET.get("token") or request.POST.get("token") or ""
    if not token:
        return _invalid(request, "missing")

    try:
        user = verify_password_setup_token(token)
    except ConsumedTokenError:
        return _invalid(request, "used")
    except ExpiredTokenError:
        return _invalid(request, "expired")
    except InvalidTokenError:
        return _invalid(request, "invalid")

    if request.method == "POST":
        form = SetPasswordForm(request.POST, user=user)
        if form.is_valid():
            try:
                with transaction.atomic():
                    user = consume_password_setup_token(token)
                    user.set_password(form.cleaned_data["password1"])
                    # ``updated_at`` is ``auto_now=True`` — include it
                    # explicitly so ``update_fields`` still fires the
                    # timestamp (see project CLAUDE.md).
                    user.save(update_fields=["password", "updated_at"])
            except ConsumedTokenError:
                return _invalid(request, "used")
            except ExpiredTokenError:
                return _invalid(request, "expired")
            except InvalidTokenError:
                return _invalid(request, "invalid")
            # `login` needs a backend attribute when called without
            # going through `authenticate`. Project has a single
            # backend (EmailBackend) — set it explicitly.
            user.backend = "apps.accounts.backends.EmailBackend"
            login(request, user)
            return redirect("/")
    else:
        form = SetPasswordForm(user=user)

    return render(
        request,
        "accounts/set_password.html",
        {"form": form, "token": token, "user": user},
    )
