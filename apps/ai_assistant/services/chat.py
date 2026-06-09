"""Compose the system prompt and call Gemini.

This module is the seam tests mock — patch ``generate`` here (not in
``client``) so view-level tests don't need to know which provider sits
behind the assistant.
"""
from __future__ import annotations

from apps.ai_assistant.services.client import GeminiUnavailable, generate
from apps.ai_assistant.services.context import build_member_context

_FALLBACK_REPLY = (
    "Sorry — our assistant is having trouble right now. "
    "Please call MerryMeal on (555) 444-MEAL and the office team can help."
)

_SYSTEM_PROMPT = """You are MerryMeal's helpful assistant. MerryMeal is a charity that delivers warm meals to seniors and people who can't cook for themselves.

Your job is to answer questions from a logged-in member about THEIR meal, THEIR delivery, the weekly menu, and how the service works. Be warm, short, and concrete — most members are seniors who prefer plain language.

Hard rules:
- Answer ONLY from the "Member data" block below. Do NOT invent meal names, delivery times, volunteer names, or ingredients that are not in the data.
- If asked something not in the data (medical advice, account changes, refunds, pausing deliveries, anything personal you don't see), say: "I don't have that detail — please call MerryMeal on (555) 444-MEAL." Do not guess.
- Do not claim to perform actions. You cannot pause deliveries, change a meal, or update an address. Direct the member to the Help page or the phone number.
- Keep replies under 80 words unless the member asks for more detail.
- Australian English. Use "mum" not "mom", "favourite" not "favorite".
- Australia/Melbourne timezone — "tomorrow" and "today" are from the member's perspective.

--- Member data ---
{context}
--- End member data ---
"""


def build_reply(user, message: str, *, history: list[dict] | None = None) -> str:
    """Return a Gemini reply for ``user`` asking ``message``.

    Catches every Gemini failure and returns a static fallback so the
    chat widget can never crash the page that hosts it. Callers should
    just render whatever this returns — there is no "error" channel.
    """
    context = build_member_context(user)
    system = _SYSTEM_PROMPT.format(context=context)
    try:
        return generate(system, message, history=history)
    except GeminiUnavailable:
        return _FALLBACK_REPLY
