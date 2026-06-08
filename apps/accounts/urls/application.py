from django.urls import path

from apps.accounts.views.application import (
    application_done,
    application_step_1,
    application_step_2,
    application_step_3,
)

urlpatterns = [
    path("", application_step_1, name="application_step_1"),
    path("address/", application_step_2, name="application_step_2"),
    path("dietary/", application_step_3, name="application_step_3"),
    path("done/", application_done, name="application_done"),
]
