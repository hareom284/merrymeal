"""Build the per-request data snapshot the assistant grounds its reply on.

The Gemini call has no tools / function-calling — we paste a markdown
snapshot of the member's real data into the system prompt instead. This
costs more tokens per request than tool-calling but keeps the wiring
trivial and makes the assistant fully reproducible from a transcript
(useful when a member calls the office to complain about an answer).
"""
from __future__ import annotations

from apps.dashboards.services.member_dashboard import (
    build_member_dashboard_context,
)


def build_member_context(user) -> str:
    """Return a markdown summary of what the member has on file today.

    Pulled from the same composer the dashboard uses, so the assistant
    can never disagree with what the member is looking at on screen.
    """
    try:
        ctx = build_member_dashboard_context(user)
    except Exception:
        # Defensive — a partner-affiliated member or other edge case
        # could blow up the composer. The assistant degrades to "I
        # don't have your data right now" rather than 500-ing the chat.
        return f"Member name: {user.full_name or user.email}\n(No live data available right now.)"

    name = (user.full_name or user.email or "member").strip()
    lines: list[str] = [f"Member name: {name}", ""]

    card = ctx.get("card") or {}
    if card.get("has_meal"):
        lines.append(f"Today's meal: {card.get('meal_name', '(unknown)')}")
        if card.get("meal_description"):
            lines.append(f"Description: {card['meal_description']}")
        if card.get("ingredient_names"):
            lines.append(
                "Ingredients: " + ", ".join(card["ingredient_names"])
            )
        if card.get("allergens"):
            allergen_names = ", ".join(a.name for a in card["allergens"])
            lines.append(
                f"⚠️ Allergens flagged on this meal: {allergen_names}"
            )
    else:
        next_date = card.get("next_plan_date")
        lines.append(
            f"No meal scheduled for today. Next planned: {next_date}"
            if next_date
            else "No meal scheduled for today."
        )

    delivery = ctx.get("delivery")
    if delivery:
        lines.append("")
        lines.append(f"Delivery status: {delivery.get('status_label', '(unknown)')}")
        for stage in delivery.get("stages", []):
            lines.append(
                f"  - {stage['name']} ({stage['state']}): {stage['subtitle']}"
            )
        volunteer = delivery.get("volunteer")
        if volunteer:
            lines.append(f"Volunteer: {volunteer.get('name', '(unknown)')}")

    week_menu = ctx.get("week_menu") or []
    if week_menu:
        lines.append("")
        lines.append("This week's menu:")
        for day in week_menu:
            lines.append(
                f"  - {day['day']}: {day['meal']} ({day['state']})"
            )

    feedback = ctx.get("feedback_prompt")
    if feedback:
        lines.append("")
        lines.append(
            f"Pending feedback: {feedback['meal']} (member hasn't rated it yet)"
        )

    return "\n".join(lines)
