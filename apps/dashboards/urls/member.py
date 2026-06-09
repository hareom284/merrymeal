from django.urls import path

from apps.dashboards.views.help import help_view
from apps.dashboards.views.member import member_dashboard_view
from apps.dashboards.views.member_dietary import member_dietary_edit_view
from apps.dashboards.views.notifications import notifications_view
from apps.dashboards.views.profile import member_profile_view
from apps.dashboards.views.weekly_menu import weekly_menu_view

urlpatterns = [
    path("dashboard/", member_dashboard_view, name="member"),
    path("help/", help_view, name="member_help"),
    path("profile/", member_profile_view, name="member_profile"),
    path(
        "profile/dietary/",
        member_dietary_edit_view,
        name="member_dietary_edit",
    ),
    path("menu/", weekly_menu_view, name="weekly_menu"),
    path("notifications/", notifications_view, name="notifications"),
]
