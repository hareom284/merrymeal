from django.urls import include, path

from apps.dashboards.views import landing_view

from .admin import urlpatterns as admin_urls
from .member import urlpatterns as member_urls

app_name = "dashboards"

urlpatterns = [
    path("", landing_view, name="landing"),
    *member_urls,
    path("admin/", include(admin_urls)),
]
