"""URL config for the donations app.

Mounted at ``/donations/`` in ``config/urls.py``. Each Sprint 09 story
appends its own ``path(...)`` here:

* Story 5.6 — ``donations:impact``  — public donor-impact preview.
* Story 5.3 — ``donations:donate``  — public donate page (pending).
* Story 5.4 — ``donations:webhook`` — Stripe webhook (pending).
* Story 5.5 — ``donations:thanks``  — post-donation receipt page (pending).
* Story 5.7 — ``donations:manage``  — recurring-donation manage page (pending).

Keep this module additive — the impact view is a leaf and must not
depend on the donate/webhook surfaces below.
"""
from django.urls import path

from apps.donations.views import impact_view

app_name = "donations"

urlpatterns = [
    # Story 5.6 — "$50 = 16 meals" preview. ``?amount_cents=<int>``.
    path("impact/", impact_view, name="impact"),
]
