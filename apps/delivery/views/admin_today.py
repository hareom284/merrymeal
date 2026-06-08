"""Story 4.14 — Admin "today" list of all deliveries scheduled today.

Custom view (not Django admin). Restricted to ``role='admin'`` by the
``role_required`` decorator (returns 403 for everyone else).
"""
from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils import timezone

from apps.core.decorators import role_required
from apps.delivery.models import Delivery


@login_required
@role_required("admin")
def admin_today_view(request):
    today = timezone.localdate()
    deliveries = (
        Delivery.objects.filter(scheduled_date=today)
        .select_related("member", "volunteer", "route")
        .order_by("route_id", "id")
    )
    return render(
        request,
        "delivery/admin/today.html",
        {"deliveries": deliveries, "today": today},
    )
