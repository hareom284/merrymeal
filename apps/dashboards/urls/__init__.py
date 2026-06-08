from django.urls import include, path

from apps.dashboards.views import landing_view

from .admin import urlpatterns as admin_urls
from .caregiver import urlpatterns as caregiver_urls
from .member import urlpatterns as member_urls

app_name = "dashboards"

# URL ordering matters: `member_urls` registers `/dashboard/` first so
# that path resolves to `member_dashboard_view`, which acts as a role
# router and delegates to the caregiver view for caregiver users. The
# caregiver patterns are still included so that the
# `dashboards:caregiver-member` named URL (and the `dashboards:caregiver`
# alias) resolve correctly during template rendering.
urlpatterns = [
    path("", landing_view, name="landing"),
    *member_urls,
    *caregiver_urls,
    path("admin/", include(admin_urls)),
]
