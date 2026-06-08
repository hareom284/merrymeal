"""URL routes for the partner outcomes dashboard.

Story 6.2 — mounted under ``/partner/`` from :mod:`config.urls`.
"""
from django.urls import path

from apps.dashboards.views.partner_outcomes import outcomes

urlpatterns = [
    path("outcomes/", outcomes, name="partner_outcomes"),
]
