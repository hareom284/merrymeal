"""Compose the system prompt and call Gemini.

Two role variants — ``build_member_reply`` for the dashboard chat
widget (grounded in the member's today card + week menu) and
``build_admin_reply`` for the admin command bar (grounded in the
attention-card counters). Both share the same fallback path so a
Gemini outage degrades to a sensible static reply rather than a 500.

The view-layer tests monkeypatch ``generate`` (imported here) so they
don't need to know whether Gemini or anything else sits behind it.
"""
from __future__ import annotations

from apps.ai_assistant.services.admin_context import build_admin_context
from apps.ai_assistant.services.client import GeminiUnavailable, generate
from apps.ai_assistant.services.context import build_member_context

_MEMBER_FALLBACK_REPLY = (
    "Sorry — our assistant is having trouble right now. "
    "Please call MerryMeal on (555) 444-MEAL and the office team can help."
)

_ADMIN_FALLBACK_REPLY = (
    "Sorry — the assistant is offline. Check the attention cards on "
    "/admin/home/ for live numbers."
)

_MEMBER_SYSTEM_PROMPT = """You are MerryMeal's helpful assistant. MerryMeal is a charity that delivers warm meals to seniors and people who can't cook for themselves.

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

_ADMIN_SYSTEM_PROMPT = """You are MerryMeal's operations assistant for admin staff. MerryMeal is a charity delivering warm meals; admins manage applications, kitchens, deliveries, and food safety.

Your job is to answer questions from a logged-in admin about today's operational state — pending applications, failed or unassigned deliveries, expiring stock, food-safety failures. Be brief and numeric; admins are busy.

Hard rules:
- Answer ONLY from the "Operational snapshot" block below. Do NOT invent counts, kitchens, or trends that aren't in the data.
- If asked something the snapshot doesn't cover (per-member history, financial reports, individual deliveries, anything that needs a deeper query), say: "I don't have that in the snapshot — open /admin/home/ for the attention cards or the relevant filtered list." Do not guess.
- Do not claim to perform actions (approving applications, reassigning deliveries, paying donors). Direct the admin to the right page instead.
- Keep replies under 80 words. Lead with the number if there is one.
- Australian English.

--- Operational snapshot ---
{context}
--- End operational snapshot ---
"""


def _generate_or_fallback(system: str, message: str, history, fallback: str) -> str:
    try:
        return generate(system, message, history=history)
    except GeminiUnavailable:
        return fallback


def build_member_reply(user, message: str, *, history: list[dict] | None = None) -> str:
    """Return a Gemini reply for a member asking ``message``."""
    context = build_member_context(user)
    system = _MEMBER_SYSTEM_PROMPT.format(context=context)
    return _generate_or_fallback(system, message, history, _MEMBER_FALLBACK_REPLY)


def build_admin_reply(user, message: str, *, history: list[dict] | None = None) -> str:
    """Return a Gemini reply for an admin asking ``message``."""
    context = build_admin_context(user)
    system = _ADMIN_SYSTEM_PROMPT.format(context=context)
    return _generate_or_fallback(system, message, history, _ADMIN_FALLBACK_REPLY)


# Backwards-compat alias for the original test suite & view import.
build_reply = build_member_reply
