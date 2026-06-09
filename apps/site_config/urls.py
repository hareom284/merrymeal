from django.urls import path

from apps.site_config.views import org_settings_edit

app_name = "site_config"

urlpatterns = [
    path("settings/", org_settings_edit, name="edit"),
]
