"""URL routes for the donor dashboard pages.

Mounted under ``/donor/`` from :mod:`apps.dashboards.urls.__init__`.
All names live in the ``dashboards`` namespace so templates and tests
can ``reverse("dashboards:donor_history")`` /
``reverse("dashboards:donor_fy_receipt", args=[fy])``.

* Story 6.3 — ``/donor/history/`` lists every donation for the
  logged-in donor.
* Story 6.4 — ``/donor/receipts/<fy>/`` renders a printer-friendly
  FY tax receipt; the ``<int:fy>`` converter rejects non-integer FYs
  with 404 at the URL layer before the view ever runs.
"""
from django.urls import path

from apps.dashboards.views.donor_history import (
    donor_history_view,
    fy_receipt,
)

urlpatterns = [
    path("history/", donor_history_view, name="donor_history"),
    path("receipts/<int:fy>/", fy_receipt, name="donor_fy_receipt"),
]
