"""URL config for the delivery app (Stories 4.8, 4.9, 4.12, 4.14).

Mounted at the project root in ``config/urls.py``. Patterns carry their
own ``volunteer/`` / ``admin/`` prefixes so the volunteer-facing screens
and the admin "today" widget can live in the same ``delivery`` namespace
without forcing ``config/urls.py`` to include this module twice.

Reverse names:
    * ``delivery:volunteer_today``    — Story 4.8
    * ``delivery:mark_delivered``     — Story 4.9
    * ``delivery:tracking_status``    — Story 4.12
    * ``delivery:admin_today``        — Story 4.14
    * ``delivery:admin_reassign``     — Story 4.14
"""
from django.urls import path

from apps.delivery.views import (
    admin_today_view,
    mark_delivered_view,
    reassign_view,
    today_view,
    tracking_status_view,
)

app_name = "delivery"

urlpatterns = [
    # --- Volunteer-facing (Story 4.8) ---------------------------------
    path("volunteer/today/", today_view, name="volunteer_today"),
    # --- POD upload + status flip (Story 4.9) -------------------------
    path(
        "volunteer/delivery/<int:pk>/mark-delivered/",
        mark_delivered_view,
        name="mark_delivered",
    ),
    # --- Member-facing tracking poll (Story 4.12) ---------------------
    path(
        "volunteer/member/delivery/<int:pk>/status/",
        tracking_status_view,
        name="tracking_status",
    ),
    # --- Admin reassign widget (Story 4.14) ---------------------------
    path("admin/today/", admin_today_view, name="admin_today"),
    path(
        "admin/delivery/<int:pk>/reassign/",
        reassign_view,
        name="admin_reassign",
    ),
]
