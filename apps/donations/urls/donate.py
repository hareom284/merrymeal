"""Public donate URL conf — namespace ``donations``.

Wired into ``config/urls.py`` under ``/donate/`` so reverse names are
``donations:donate`` and ``donations:donate_start``.
"""

from django.urls import path

from apps.donations.views.donate import donate_page, donate_start

app_name = "donations"

urlpatterns = [
    path("", donate_page, name="donate"),
    path("start/", donate_start, name="donate_start"),
]
