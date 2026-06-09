"""AI assistant chat endpoints (HTMX targets).

Two POSTs — ``chat_send`` for members and ``admin_chat_send`` for
admins — share the same session-backed conversational memory shape
(``request.session[_HISTORY_KEY]``) and the same ``_exchange.html``
render contract. The widget picks which URL to post to based on the
viewer's role.
"""
from __future__ import annotations

import re

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST

from apps.ai_assistant.services.chat import build_admin_reply, build_member_reply
from apps.ai_assistant.services.rate_limit import check as check_rate_limit
from apps.core.decorators import role_required

_MAX_MESSAGE_LEN = 600
# Six entries = three user/model exchange pairs. Keeps follow-up
# questions ("and tomorrow?") working without ballooning the Gemini
# request: every turn re-sends the per-request data snapshot in the
# system prompt, so old history is mostly redundant after a few turns.
_HISTORY_MAX_TURNS = 6
_MEMBER_HISTORY_KEY = "ai_member_history"
_ADMIN_HISTORY_KEY = "ai_admin_history"

# Strip ASCII control characters (0x00-0x1F + 0x7F) except newline and
# tab. Without this, a member could paste an OS escape sequence or a
# null byte into the message and the bytes would flow through to the
# Gemini request unchanged; Gemini ignores them but the dev log shows
# garbage. Newlines stay so multi-line questions render properly.
_CTRL_CHARS_RE = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]")


def _normalise(message: str | None) -> str:
    if not message:
        return ""
    # Strip control chars first, THEN cap length. Trimming first would
    # let a 600-char message of mostly nulls survive after stripping.
    cleaned = _CTRL_CHARS_RE.sub("", message).strip()
    return cleaned[:_MAX_MESSAGE_LEN]


def _append_turn(session, key: str, role: str, text: str) -> None:
    history = list(session.get(key, []))
    history.append({"role": role, "text": text})
    session[key] = history[-_HISTORY_MAX_TURNS:]


def _render_rate_limited(request, message: str, retry_after: int, scope: str):
    """Return the ``_exchange.html`` partial with a soft "going a bit
    fast" reply instead of crashing the widget. The user's bubble is
    still rendered so they can see what they typed; the reply tells
    them to wait.

    ``scope`` selects the copy — a global trip mentions "the assistant
    is busy" (truthful), a per-user trip is gentler ("you're going a
    bit fast").
    """
    if scope == "global":
        reply = (
            "The assistant is a bit busy right now. "
            f"Please try again in {retry_after} seconds."
        )
    else:
        reply = (
            "You're going a bit fast — please wait "
            f"{retry_after} seconds before asking again."
        )
    response = render(
        request,
        "ai_assistant/_exchange.html",
        {"message": message, "reply": reply},
    )
    # Standard HTTP signal for clients and CDNs. HTMX still swaps the
    # partial because we set status 200; the header is informational.
    response["Retry-After"] = str(retry_after)
    return response


@login_required
@require_POST
def chat_send(request):
    """POST /assistant/chat/ — member-facing chat. Appends to session
    history so follow-ups ("and tomorrow?") have context."""
    message = _normalise(request.POST.get("message"))
    if not message:
        return render(request, "ai_assistant/_empty.html")

    verdict = check_rate_limit(request.user.id)
    if not verdict.allowed:
        return _render_rate_limited(request, message, verdict.retry_after, verdict.scope)

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

    verdict = check_rate_limit(request.user.id)
    if not verdict.allowed:
        return _render_rate_limited(request, message, verdict.retry_after, verdict.scope)

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
