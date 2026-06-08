from django.urls import path

from apps.volunteers.views import availability_view, toggle_view

app_name = "volunteers"

urlpatterns = [
    path("availability/", availability_view, name="availability"),
    path("availability/toggle/", toggle_view, name="availability_toggle"),
]
