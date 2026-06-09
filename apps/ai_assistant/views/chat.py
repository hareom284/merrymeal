"""Member assistant chat endpoint (HTMX target)."""
from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.views.decorators.http import require_POST

from apps.ai_assistant.services.chat import build_reply

_MAX_MESSAGE_LEN = 600


@login_required
@require_POST
def chat_send(request):
    """POST /assistant/chat/. Returns an HTMX partial — a user bubble
    plus an assistant bubble — that the widget appends to its log."""
    message = (request.POST.get("message") or "").strip()
    if not message:
        # HTMX swap-empty: render nothing so the log is unchanged. The
        # ``required`` attribute on the input prevents this in practice,
        # but the guard keeps the contract robust against curl/scripts.
        return render(request, "ai_assistant/_empty.html")

    # Truncate aggressively — Gemini's free-tier quota is per-request,
    # so a wall-of-text from a misbehaving client must not eat the
    # member's daily budget.
    message = message[:_MAX_MESSAGE_LEN]
    reply = build_reply(request.user, message)
    return render(
        request,
        "ai_assistant/_exchange.html",
        {"message": message, "reply": reply},
    )
