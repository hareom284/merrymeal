from django.urls import path

from apps.dashboards.views.admin_applications import (
    admin_application_approve,
    admin_application_detail,
    admin_application_reject,
    admin_applications_list,
)
from apps.dashboards.views.admin_kitchens import admin_kitchens

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
]
