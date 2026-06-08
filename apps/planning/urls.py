"""URLConf for the admin weekly-planner UI (Story 3.3).

Mounted from ``config.urls`` at ``/admin/planner/``. Sits *outside* Django's
own admin site (which we intentionally do not mount — see config/urls.py).
"""

from django.urls import path

from apps.planning.views.admin_planner import (
    cell_acknowledge_view,
    cell_edit_view,
    planner_view,
)

app_name = "planning"

urlpatterns = [
    path("", planner_view, name="planner"),
    path("cell/", cell_edit_view, name="cell-edit"),
    path("cell/acknowledge/", cell_acknowledge_view, name="cell-acknowledge"),
]
