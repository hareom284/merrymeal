"""URL routes for the caregiver multi-member dashboard.

Story 3.8.

Note: `dashboards:caregiver` resolves to `/dashboard/`. The same path is
also registered by `urls/member.py` as `dashboards:member`; that view
(see `views/member.py`) inspects `request.user.role` and dispatches to
`caregiver_list_view` for caregivers. Both URL names therefore reverse to
the same path but route to the appropriate handler at request time.
"""
from django.urls import path

from apps.dashboards.views.caregiver import (
    caregiver_list_view,
    caregiver_member_detail_view,
)

urlpatterns = [
    path("dashboard/", caregiver_list_view, name="caregiver"),
    path(
        "dashboard/member/<int:pk>/",
        caregiver_member_detail_view,
        name="caregiver-member",
    ),
]
