from django.urls import path

from apps.food_safety.views.check import check_view

app_name = "food_safety"

urlpatterns = [
    path("check/", check_view, name="safety-check"),
]
