"""URL conf for the admin campaign-progress card (Story 5.8).

Mounted at ``/admin/campaigns/`` from ``config/urls.py``. Carries its own
``app_name`` namespace so the templates can resolve URLs as
``dashboards_admin_campaigns:index`` (etc.) — distinct from the existing
``dashboards`` namespace, which is reserved for member / caregiver / admin
URLs that share the dashboards landing router.
"""

from django.urls import path

from apps.dashboards.views.admin_campaigns import detail, export_csv, index

app_name = "dashboards_admin_campaigns"

urlpatterns = [
    path("", index, name="index"),
    path("<slug:slug>/", detail, name="detail"),
    path("<slug:slug>/export.csv", export_csv, name="export_csv"),
]
