"""Member notifications page (Story 12.6)."""
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_http_methods

from apps.dashboards.services.notifications import build_member_notifications


@login_required
@require_http_methods(["GET", "POST"])
def notifications_view(request):
    """GET renders the list. POST is a no-op "mark all read" that
    returns 204 — there's nothing to persist because the list is
    synthesised from existing data each request, but we honour the
    POST so the topbar bell's "Mark read" can fire-and-forget without
    a 405."""
    if request.method == "POST":
        return HttpResponse(status=204)
    return render(
        request,
        "dashboards/notifications.html",
        {
            "active": "notifications",
            "page_title": "Notifications",
            "notifications": build_member_notifications(request.user),
        },
    )
