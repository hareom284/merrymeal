"""Admin-side data snapshot for the AI command bar.

Reuses the same private counter helpers that power the admin home
attention cards (Story 6.1). Keeping the dashboard and the AI bot
sourced from the same functions means an admin asking "how many
failed deliveries today?" can never get a different answer than the
red number on the attention card next to them.
"""
from __future__ import annotations


def build_admin_context(user) -> str:
    """Return a markdown summary of the charity's current operational state."""
    from apps.dashboards.services.admin_summary import (
        _count_expiring_stock,
        _count_failed_deliveries_today,
        _count_fs_failures_24h,
        _count_pending_applications,
        _count_unassigned_deliveries_today,
    )

    name = (user.full_name or user.email or "admin").strip()
    lines: list[str] = [f"Admin name: {name}", ""]

    try:
        lines.append(
            f"Pending applications awaiting review: {_count_pending_applications()}"
        )
    except Exception:
        lines.append("Pending applications awaiting review: (query failed)")

    try:
        lines.append(
            f"Failed deliveries today: {_count_failed_deliveries_today()}"
        )
    except Exception:
        lines.append("Failed deliveries today: (query failed)")

    try:
        lines.append(
            "Unassigned deliveries scheduled for today: "
            f"{_count_unassigned_deliveries_today()}"
        )
    except Exception:
        lines.append("Unassigned deliveries scheduled for today: (query failed)")

    try:
        lines.append(
            f"Ingredient batches expiring within 3 days: {_count_expiring_stock()}"
        )
    except Exception:
        lines.append("Ingredient batches expiring within 3 days: (query failed)")

    try:
        lines.append(
            f"Food-safety check failures in the last 24h: {_count_fs_failures_24h()}"
        )
    except Exception:
        lines.append("Food-safety check failures in the last 24h: (query failed)")

    return "\n".join(lines)
