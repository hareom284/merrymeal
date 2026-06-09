"""Admin notifications page (Story 12.9).

Mirrors the member ``/notifications/`` shape: GET renders the list, POST
returns 204 as a no-op "mark all read" — there's nothing to persist
because the list is synthesised on each request from
``admin_summary.build()``.
"""
from django.http import HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_http_methods

from apps.core.decorators import role_required
from apps.dashboards.services.admin_notifications import build_admin_notifications


@role_required("admin")
@require_http_methods(["GET", "POST"])
def admin_notifications_view(request):
    if request.method == "POST":
        return HttpResponse(status=204)
    return render(
        request,
        "dashboards/admin/notifications.html",
        {
            "active": "notifications",
            "page_title": "Notifications",
            "notifications": build_admin_notifications(),
        },
    )
