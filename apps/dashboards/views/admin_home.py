"""Story 6.1 — admin home: "what needs attention now"."""
from django.shortcuts import render

from apps.core.decorators import role_required
from apps.dashboards.services import admin_summary


@role_required("admin")
def admin_home(request):
    """Render the five "needs attention" cards inside the admin chrome."""
    cards = admin_summary.build()
    return render(
        request,
        "dashboards/admin/home.html",
        {"cards": cards, "active": "home", "page_title": "Admin home"},
    )


@role_required("admin")
def admin_home_cards(request):
    """HTMX partial — the same cards without the page chrome.

    Wired from ``home.html`` via ``hx-get`` + ``hx-trigger="every 300s"``
    so the dashboard self-refreshes every 5 minutes.
    """
    cards = admin_summary.build()
    return render(
        request,
        "dashboards/admin/_attention_card.html",
        {"cards": cards, "partial": True},
    )
