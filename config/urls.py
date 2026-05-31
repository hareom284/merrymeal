from django.urls import include, path

# Django's built-in admin is intentionally NOT mounted.
# All operational/admin UIs are built as custom views under /
# (e.g. /admin/applications/, /admin/kitchens/) using the brand design.
# Data management via CLI: `python3 manage.py shell`, `createsuperuser`,
# custom management commands.

urlpatterns = [
    path("accounts/", include("apps.accounts.urls")),
    path("", include("apps.dashboards.urls")),
]
