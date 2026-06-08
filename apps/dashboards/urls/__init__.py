from django.urls import path

from apps.dashboards.views import landing_view

from .member import urlpatterns as member_urls

app_name = "dashboards"

urlpatterns = [
    path("", landing_view, name="landing"),
    *member_urls,
]
