"""AI assistant chat endpoints (HTMX targets).

Two POSTs — ``chat_send`` for members and ``admin_chat_send`` for
admins — share the same session-backed conversational memory shape
(``request.session[_HISTORY_KEY]``) and the same ``_exchange.html``
render contract. The widget picks which URL to post to based on the
viewer's role.
"""
from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST

from apps.ai_assistant.services.chat import build_admin_reply, build_member_reply
from apps.core.decorators import role_required

_MAX_MESSAGE_LEN = 600
# Six entries = three user/model exchange pairs. Keeps follow-up
# questions ("and tomorrow?") working without ballooning the Gemini
# request: every turn re-sends the per-request data snapshot in the
# system prompt, so old history is mostly redundant after a few turns.
_HISTORY_MAX_TURNS = 6
_MEMBER_HISTORY_KEY = "ai_member_history"
_ADMIN_HISTORY_KEY = "ai_admin_history"


def _normalise(message: str | None) -> str:
    return (message or "").strip()[:_MAX_MESSAGE_LEN]


def _append_turn(session, key: str, role: str, text: str) -> None:
    history = list(session.get(key, []))
    history.append({"role": role, "text": text})
    session[key] = history[-_HISTORY_MAX_TURNS:]


@login_required
@require_POST
def chat_send(request):
    """POST /assistant/chat/ — member-facing chat. Appends to session
    history so follow-ups ("and tomorrow?") have context."""
    message = _normalise(request.POST.get("message"))
    if not message:
        return render(request, "ai_assistant/_empty.html")

    history = list(request.session.get(_MEMBER_HISTORY_KEY, []))
    reply = build_member_reply(request.user, message, history=history)

    _append_turn(request.session, _MEMBER_HISTORY_KEY, "user", message)
    _append_turn(request.session, _MEMBER_HISTORY_KEY, "model", reply)

    return render(
        request,
        "ai_assistant/_exchange.html",
        {"message": message, "reply": reply},
    )


@login_required
@role_required("admin")
@require_POST
def admin_chat_send(request):
    """POST /admin/assistant/chat/ — admin command bar. Same shape as
    the member endpoint but uses the admin context and a separate
    history slot so the two transcripts don't bleed into each other."""
    message = _normalise(request.POST.get("message"))
    if not message:
        return render(request, "ai_assistant/_empty.html")

    history = list(request.session.get(_ADMIN_HISTORY_KEY, []))
    reply = build_admin_reply(request.user, message, history=history)

    _append_turn(request.session, _ADMIN_HISTORY_KEY, "user", message)
    _append_turn(request.session, _ADMIN_HISTORY_KEY, "model", reply)

    return render(
        request,
        "ai_assistant/_exchange.html",
        {"message": message, "reply": reply},
    )


@login_required
@require_POST
def chat_clear(request):
    """POST /assistant/clear/ — wipe the caller's conversation history
    (both member and admin slots). Returns 204 so HTMX can react
    without a full swap; the widget rebuilds the log from scratch on
    the next open."""
    request.session.pop(_MEMBER_HISTORY_KEY, None)
    request.session.pop(_ADMIN_HISTORY_KEY, None)
    return HttpResponse(status=204)
