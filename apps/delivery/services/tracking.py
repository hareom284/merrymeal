"""Service: shape the member tracking card (Story 4.12).

Pure read; no side effects. Returns the context the view passes straight
to ``templates/delivery/member/_tracking_card.html``.

Adaptations from the spec
-------------------------
* The ``User`` model is ``full_name`` only — no separate ``first_name``
  / ``last_name``. We derive "Sarah K." by splitting on whitespace and
  taking the first token + the first letter of the last token. The
  same helper Story 4.8 (volunteer today) uses.
* For single-token names ("Cher") we render just the first name with
  **no trailing period** — explicitly called out as a reviewer pitfall.
"""
from __future__ import annotations

from typing import Any

from apps.delivery.models import Delivery

#: Statuses that end polling — the partial swapped in carries no
#: ``hx-trigger`` so HTMX has nothing left to fire.
TERMINAL_STATUSES: frozenset[str] = frozenset({"delivered", "failed"})


def _volunteer_display(volunteer) -> str:
    """Return ``"Sarah K."`` from ``full_name="Sarah Khan"``.

    Falls back gracefully:
    * ``None`` / empty name → empty string.
    * Single-token name ("Cher") → ``"Cher"`` (no stray period).
    """
    if volunteer is None:
        return ""
    full = (getattr(volunteer, "full_name", "") or "").strip()
    if not full:
        return ""
    parts = full.split()
    if len(parts) == 1:
        return parts[0]
    return f"{parts[0]} {parts[-1][:1]}."


def _label_for(status: str, volunteer_display: str) -> str:
    if status == "pending":
        return "Cooking — pickup soon"
    if status == "out_for_delivery":
        if volunteer_display:
            return f"On the way with {volunteer_display}"
        return "On the way"
    if status == "delivered":
        return "Delivered"
    if status == "failed":
        return "Couldn't deliver — we'll call you"
    return status


def get_tracking_context(delivery: Delivery, viewer) -> dict[str, Any]:
    """Return the context dict for the member tracking partial.

    Shape (stable):
      {
        "delivery": Delivery,
        "status": str,
        "label": str,
        "volunteer_display": str,
        "delivered_at": datetime | None,
        "polling": bool,            # False once status in {delivered, failed}
      }

    ``viewer`` is accepted for symmetry with Story 4.18 (consent gates the
    reveal of phone numbers); the current sprint only consumes ``delivery``.
    """
    status = delivery.status
    vol_display = _volunteer_display(delivery.volunteer)

    return {
        "delivery": delivery,
        "status": status,
        "label": _label_for(status, vol_display),
        "volunteer_display": vol_display,
        "delivered_at": delivery.delivered_time,
        "polling": status not in TERMINAL_STATUSES,
    }
