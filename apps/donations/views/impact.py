"""Standalone donor-impact preview view (Story 5.6).

A thin GET-only page that renders "your $X = N meals" using the same
``meals_for_amount`` helper the donate chips (5.3), thanks page (5.5)
and receipt email (5.5) share. Lives at ``/donations/impact/`` so the
public marketing site / a tracked link can preview the conversion
without booting the donate-flow funnel.

The view is intentionally forgiving — a stray non-numeric or negative
``amount_cents`` falls back to zero rather than 500ing. The strict
boundary is the service; the view is the public surface.
"""
from __future__ import annotations

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from apps.donations.services.impact import meals_for_amount


def _parse_amount_cents(raw: str | None) -> int:
    """Coerce the ``?amount_cents=`` query string to a safe non-negative int.

    Returns 0 for missing / empty / non-numeric / negative input —
    keeps the page from 500ing on a mistyped URL or a stale tracker
    redirect. Validation that *raises* belongs in the service; this
    view is the relaxed boundary.
    """
    if not raw:
        return 0
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return 0
    return value if value >= 0 else 0


def impact_view(request: HttpRequest) -> HttpResponse:
    """Render the impact preview page.

    Reads ``?amount_cents=<int>`` from the query string and renders the
    "$X = N meals" caption. The view stays thin per MerryMeal
    conventions: parse the input, hand to the service, render. No
    side effects, no DB writes.
    """
    amount_cents = _parse_amount_cents(request.GET.get("amount_cents"))
    meal_count = meals_for_amount(amount_cents)
    return render(
        request,
        "donations/impact.html",
        {
            "amount_cents": amount_cents,
            "meal_count": meal_count,
        },
    )
