from django.urls import path

from apps.dashboards.views.member import member_dashboard_view

urlpatterns = [
    path("dashboard/", member_dashboard_view, name="member"),
]
