"""Audit log viewer (Story 6.6).

Read-only admin view over ``auditlog.LogEntry``. The view is
deliberately GET-only — there is no POST handler, no edit URL, and
no delete URL anywhere in the dashboards URL conf. See
``apps/dashboards/tests/test_audit.py`` for the read-only guards.
"""
from datetime import date

from django.core.paginator import Paginator
from django.shortcuts import render
from django.views.decorators.http import require_GET

from apps.core.decorators import role_required
from apps.dashboards.services import audit_query

# Surfaced to the template so the action dropdown stays in sync with
# the service's accepted vocabulary without needing a custom template
# filter to split a string.
ACTION_OPTIONS = ("create", "update", "delete", "access")


def _parse_date(value: str | None) -> date | None:
    """Parse an ``YYYY-MM-DD`` string into a ``date`` or return ``None``.

    Invalid input is treated as "no filter" rather than raising — the
    viewer is exploratory and a bad date in the query string should
    not 500.
    """
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


@require_GET  # explicitly disallow POST/PUT/DELETE — read-only viewer.
@role_required("admin")
def audit_viewer(request):
    qs = audit_query.filtered(
        email=request.GET.get("email") or None,
        object_type=request.GET.get("object_type") or None,
        date_from=_parse_date(request.GET.get("from")),
        date_to=_parse_date(request.GET.get("to")),
        action=request.GET.get("action") or None,
    )
    paginator = Paginator(qs, 50)
    page = paginator.get_page(request.GET.get("page") or 1)

    # Pre-compute a clean query string for the prev/next pagination
    # links so they preserve every active filter without colliding
    # with the ``page`` parameter.
    base_params = request.GET.copy()
    base_params.pop("page", None)
    base_querystring = base_params.urlencode()

    return render(
        request,
        "dashboards/admin/audit.html",
        {
            "page_obj": page,
            "filters": {
                "email": request.GET.get("email", ""),
                "object_type": request.GET.get("object_type", ""),
                "from": request.GET.get("from", ""),
                "to": request.GET.get("to", ""),
                "action": request.GET.get("action", ""),
            },
            "action_options": ACTION_OPTIONS,
            "base_querystring": base_querystring,
            "active": "audit",
            "page_title": "Audit log",
        },
    )
