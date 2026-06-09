"""Synthesised admin notifications (Story 12.9).

The bell in the admin shell points here. Each item is derived from the
existing ``admin_summary.build()`` cards — we deliberately reuse that
service so the bell, the home cards, and the drill-down counts can
never disagree.

An item appears only when ``count > 0`` — the bell badge is purely a
"there's at least one thing to do" signal; the page itself shows the
per-kind counts. Returning plain dicts keeps the template dumb and
makes it trivial to fold new attention sources in later.

Public entrypoints:
    build_admin_notifications() -> list[dict]
    admin_notification_count() -> int
"""
from __future__ import annotations

from typing import Any

from apps.dashboards.services import admin_summary

# Each admin_summary card title maps to a stable kind + icon so the
# template doesn't switch on the human-readable title. Adding a new
# admin_summary card means adding a row here.
_KIND_BY_TITLE = {
    "Pending applications": ("applications", "users"),
    "Expiring stock": ("expiring_stock", "kitchen"),
    "Failed deliveries today": ("failed_delivery", "truck"),
    "Unassigned deliveries today": ("unassigned_delivery", "truck"),
    "Recent food-safety failures": ("fs_failure", "shield"),
}

_BODY_BY_KIND = {
    "applications": "Members waiting on approval.",
    "expiring_stock": "Ingredient batches close to their use-by date.",
    "failed_delivery": "Deliveries marked failed today.",
    "unassigned_delivery": "Scheduled today, still without a route.",
    "fs_failure": "Failed food-safety checks in the last 24 hours.",
}


def build_admin_notifications() -> list[dict[str, Any]]:
    """Return the ordered list of admin notification dicts.

    Order mirrors ``admin_summary.build()`` (most-actionable categories
    first — applications, then stock, then delivery, then food safety).
    Empty kinds (count == 0) are dropped so the bell badge and the
    page reflect the same "things to do" set.
    """
    items: list[dict[str, Any]] = []
    for card in admin_summary.build():
        if card.count == 0:
            continue
        kind, icon = _KIND_BY_TITLE.get(card.title, ("attention", "shield"))
        items.append({
            "kind": kind,
            "title": card.title,
            "body": _BODY_BY_KIND.get(kind, ""),
            "count": card.count,
            "severity": card.severity,
            "icon": icon,
            "url": card.link,
        })
    return items


def admin_notification_count() -> int:
    """Single integer for the bell badge. Sum of all kinds with hits."""
    return sum(card.count for card in admin_summary.build() if card.count > 0)
