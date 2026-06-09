"""URL config for the delivery app (Stories 4.8, 4.9, 4.10, 4.11, 4.12, 4.14).

Mounted at the project root in ``config/urls.py``. Patterns carry their
own ``volunteer/`` / ``admin/`` prefixes so the volunteer-facing screens
and the admin "today" widget can live in the same ``delivery`` namespace
without forcing ``config/urls.py`` to include this module twice.

Reverse names:
    * ``delivery:volunteer_today``    — Story 4.8
    * ``delivery:mark_delivered``     — Story 4.9
    * ``delivery:mark_failed``        — Story 4.10
    * ``delivery:feedback``           — Story 4.11
    * ``delivery:tracking_status``    — Story 4.12
    * ``delivery:admin_today``        — Story 4.14
    * ``delivery:admin_reassign``     — Story 4.14
    * ``delivery:rate_meal``          — Story 12.8
"""
from django.urls import path

from apps.delivery.views import (
    admin_today_view,
    feedback_view,
    mark_delivered_view,
    mark_failed_view,
    rate_meal_view,
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
    # --- Couldn't-deliver bottom sheet (Story 4.10) -------------------
    path(
        "volunteer/delivery/<int:pk>/mark-failed/",
        mark_failed_view,
        name="mark_failed",
    ),
    # --- Member-facing tracking poll (Story 4.12) ---------------------
    path(
        "member/delivery/<int:pk>/status/",
        tracking_status_view,
        name="tracking_status",
    ),
    # --- 2-tap meal feedback (Story 4.11) -----------------------------
    path(
        "member/feedback/<int:pk>/",
        feedback_view,
        name="feedback",
    ),
    # --- Standalone rate-meal page (Story 12.8) -----------------------
    path(
        "rate/<int:delivery_id>/",
        rate_meal_view,
        name="rate_meal",
    ),
    # --- Admin reassign widget (Story 4.14) ---------------------------
    path("admin/today/", admin_today_view, name="admin_today"),
    path(
        "admin/delivery/<int:pk>/reassign/",
        reassign_view,
        name="admin_reassign",
    ),
]
