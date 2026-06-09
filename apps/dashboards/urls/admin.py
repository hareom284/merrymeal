from django.urls import path

from apps.dashboards.views.admin_applications import (
    admin_application_approve,
    admin_application_detail,
    admin_application_reject,
    admin_applications_list,
)
from apps.dashboards.views.admin_attention import (
    admin_expiring_stock,
    admin_failed_deliveries_today,
    admin_fs_failures_recent,
    admin_unassigned_deliveries_today,
)
from apps.dashboards.views.admin_food_safety import (
    admin_fs_create,
    admin_fs_detail,
    admin_fs_list,
)
from apps.dashboards.views.admin_home import admin_home, admin_home_cards
from apps.dashboards.views.admin_ingredient_batches import (
    admin_batch_create,
    admin_batch_detail,
    admin_batches_list,
)
from apps.dashboards.views.admin_kitchens import admin_kitchens
from apps.dashboards.views.admin_members import (
    admin_member_deactivate,
    admin_member_detail,
    admin_member_reactivate,
    admin_members_list,
)
from apps.dashboards.views.admin_notifications import admin_notifications_view
from apps.dashboards.views.admin_partners import (
    admin_partner_create,
    admin_partner_detail,
    admin_partner_edit,
    admin_partners_list,
)
from apps.dashboards.views.admin_profile import admin_profile_view
from apps.dashboards.views.admin_volunteers import (
    admin_volunteer_deactivate,
    admin_volunteer_detail,
    admin_volunteer_reactivate,
    admin_volunteers_list,
)
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
    # Story 12.11 — members directory (read + deactivate/reactivate).
    # Members are linked from /admin/home/ rather than a top-level
    # nav tab to keep the bottom nav at 5 cells.
    path("members/", admin_members_list, name="admin_members"),
    path("members/<int:pk>/", admin_member_detail, name="admin_member_detail"),
    path(
        "members/<int:pk>/deactivate/",
        admin_member_deactivate,
        name="admin_member_deactivate",
    ),
    path(
        "members/<int:pk>/reactivate/",
        admin_member_reactivate,
        name="admin_member_reactivate",
    ),
    # Story 12.12 — admin food-safety browser. List + filter + add new.
    # NO edit/delete by design: food-safety records are compliance
    # artefacts; corrections happen via a new superseding check.
    path("food_safety/", admin_fs_list, name="admin_fs_list"),
    path("food_safety/new/", admin_fs_create, name="admin_fs_create"),
    path("food_safety/<int:pk>/", admin_fs_detail, name="admin_fs_detail"),
    # Story 12.13 — admin volunteers directory.
    path("volunteers/", admin_volunteers_list, name="admin_volunteers"),
    path(
        "volunteers/<int:pk>/",
        admin_volunteer_detail,
        name="admin_volunteer_detail",
    ),
    path(
        "volunteers/<int:pk>/deactivate/",
        admin_volunteer_deactivate,
        name="admin_volunteer_deactivate",
    ),
    path(
        "volunteers/<int:pk>/reactivate/",
        admin_volunteer_reactivate,
        name="admin_volunteer_reactivate",
    ),
    # Story 12.15 — partners directory (charities / restaurants /
    # suppliers / corporates). CRU only — Partner is PROTECTed by
    # Application.partner and User.partner FKs so a hard delete fails
    # if any data refers to it; cleanup happens upstream.
    path("partners/", admin_partners_list, name="admin_partners"),
    path("partners/new/", admin_partner_create, name="admin_partner_create"),
    path(
        "partners/<int:pk>/",
        admin_partner_detail,
        name="admin_partner_detail",
    ),
    path(
        "partners/<int:pk>/edit/",
        admin_partner_edit,
        name="admin_partner_edit",
    ),
    # Story 12.16 — admin ingredient-batch browser. List + filter + add.
    # No edit/delete by design: stock movements are recorded as events,
    # not by mutating history (same contract as food-safety).
    path("stock/", admin_batches_list, name="admin_batches"),
    path("stock/new/", admin_batch_create, name="admin_batch_create"),
    path("stock/<int:pk>/", admin_batch_detail, name="admin_batch_detail"),
    # Story 6.6 — read-only audit log viewer.
    # Deliberately NO ``audit/<id>/edit/`` or ``audit/<id>/delete/`` routes.
    # The viewer is GET-only; mutations go through the underlying audited
    # models, not through this URL space.
    path("audit/", audit_viewer, name="audit_viewer"),
    # Story 6.1 — admin home "what needs attention now". The chrome page
    # renders five cards; the HTMX partial re-fetches every 5 minutes.
    path("home/", admin_home, name="admin_home"),
    path("home/cards/", admin_home_cards, name="admin_home_cards"),
    # Story 12.9 — admin notifications feed (synthesised from
    # admin_summary so the bell can never disagree with /admin/home/).
    path(
        "notifications/",
        admin_notifications_view,
        name="admin_notifications",
    ),
    # Story 12.10 — admin profile (read-only for v1).
    path("profile/", admin_profile_view, name="admin_profile"),
    # Story 6.5 — one-click monthly board pack (CSV / PDF / printable HTML).
    path("reports/board/", board_report_view, name="board_report"),
    # Admin home "needs attention" click-through targets. The named routes
    # below MUST match the strings ``admin_summary.build()`` reverses; if a
    # name changes, the card silently degrades to ``link="#"`` via the
    # ``NoReverseMatch`` guard in the service.
    path(
        "attention/expiring-stock/",
        admin_expiring_stock,
        name="expiring_stock",
    ),
    path(
        "attention/failed-deliveries/",
        admin_failed_deliveries_today,
        name="failed_deliveries_today",
    ),
    path(
        "attention/unassigned-deliveries/",
        admin_unassigned_deliveries_today,
        name="unassigned_deliveries_today",
    ),
    path(
        "attention/food-safety-failures/",
        admin_fs_failures_recent,
        name="fs_failures_recent",
    ),
]
