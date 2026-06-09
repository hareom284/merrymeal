from django.urls import path

from apps.dashboards.views.help import help_view
from apps.dashboards.views.member import member_dashboard_view
from apps.dashboards.views.profile import member_profile_view

urlpatterns = [
    path("dashboard/", member_dashboard_view, name="member"),
    path("help/", help_view, name="member_help"),
    path("profile/", member_profile_view, name="member_profile"),
]
