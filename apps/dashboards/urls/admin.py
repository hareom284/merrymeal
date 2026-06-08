from django.urls import path

from apps.dashboards.views.admin_applications import (
    admin_application_approve,
    admin_application_detail,
    admin_application_reject,
    admin_applications_list,
)
from apps.dashboards.views.admin_home import admin_home, admin_home_cards
from apps.dashboards.views.admin_kitchens import admin_kitchens
from apps.dashboards.views.audit import audit_viewer
from apps.dashboards.views.board_report import board_report_view

urlpatterns = [
    path("applications/", admin_applications_list, name="admin_applications"),
    path(
        "applications/<int:pk>/",
        admin_application_detail,
        name="admin_application_detail",
    ),
    path(
        "applications/<int:pk>/approve/",
        admin_application_approve,
        name="admin_application_approve",
    ),
    path(
        "applications/<int:pk>/reject/",
        admin_application_reject,
        name="admin_application_reject",
    ),
    path("kitchens/", admin_kitchens, name="admin_kitchens"),
    # Story 6.6 — read-only audit log viewer.
    # Deliberately NO ``audit/<id>/edit/`` or ``audit/<id>/delete/`` routes.
    # The viewer is GET-only; mutations go through the underlying audited
    # models, not through this URL space.
    path("audit/", audit_viewer, name="audit_viewer"),
    # Story 6.1 — admin home "what needs attention now". The chrome page
    # renders five cards; the HTMX partial re-fetches every 5 minutes.
    path("home/", admin_home, name="admin_home"),
    path("home/cards/", admin_home_cards, name="admin_home_cards"),
    # Story 6.5 — one-click monthly board pack (CSV / PDF / printable HTML).
    path("reports/board/", board_report_view, name="board_report"),
]
