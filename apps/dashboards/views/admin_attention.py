"""Admin attention list views — click-through targets for the home cards.

The admin home ("what needs attention now") renders five summary cards from
``apps.dashboards.services.admin_summary``. Each card needs a destination
URL so admins can drill from the count into the underlying rows. One card
(pending applications) already has a list view; the four small views here
back the remaining cards.

Each view mirrors the filter used by the matching ``_count_*`` helper in
``admin_summary.py`` exactly — counts and list contents must agree, or the
dashboard lies. Querysets stay thin (single filter, ``select_related`` for
the FKs the template prints, no annotations) because the page is admin-only
and traffic is low.

Time queries use ``timezone.localdate()`` (date columns) or
``timezone.now()`` (datetime columns); both honour ``Australia/Melbourne``
via ``settings.TIME_ZONE``.
"""
from __future__ import annotations

from datetime import timedelta

from django.shortcuts import render
from django.utils import timezone

from apps.core.decorators import role_required


@role_required("admin")
def admin_expiring_stock(request):
    """Ingredient batches expiring within the next 3 days.

    Mirrors ``admin_summary._count_expiring_stock``: ``expiration_date <=
    today + 3``. Ordered by ``expiration_date`` so the most urgent batches
    surface first.
    """
    from apps.kitchens.models import IngredientBatch

    today = timezone.localdate()
    batches = (
        IngredientBatch.objects
        .filter(expiration_date__lte=today + timedelta(days=3))
        .select_related("ingredient", "kitchen")
        .order_by("expiration_date", "id")
    )
    return render(
        request,
        "dashboards/admin/attention_expiring_stock.html",
        {"page_title": "Expiring stock", "batches": batches, "today": today, "active": "home"},
    )


@role_required("admin")
def admin_failed_deliveries_today(request):
    """Deliveries with ``status='failed'`` scheduled for today.

    Mirrors ``admin_summary._count_failed_deliveries_today``.
    """
    from apps.delivery.models import Delivery

    today = timezone.localdate()
    deliveries = (
        Delivery.objects
        .filter(status=Delivery.STATUS_FAILED, scheduled_date=today)
        .select_related("member", "volunteer", "meal_plan__kitchen")
        .order_by("-updated_at", "-id")
    )
    return render(
        request,
        "dashboards/admin/attention_failed_deliveries.html",
        {
            "page_title": "Failed deliveries today",
            "deliveries": deliveries,
            "today": today,
            "active": "home",
        },
    )


@role_required("admin")
def admin_unassigned_deliveries_today(request):
    """Deliveries scheduled today and still unassigned to a route.

    NOTE: Story 4.7 envisaged a nullable ``volunteer_id`` to model the
    overflow queue. The current Delivery schema has volunteer as
    PROTECT/non-null (see ``apps/delivery/models/deliveries.py``); the
    closest available signal is "scheduled today but still pending
    dispatch" — deliveries the route board has not yet moved to
    ``out_for_delivery``. When the overflow queue lands, swap this to a
    ``volunteer_id__isnull=True`` filter. Mirrors
    ``admin_summary._count_unassigned_deliveries_today``.
    """
    from apps.delivery.models import Delivery

    today = timezone.localdate()
    deliveries = (
        Delivery.objects
        .filter(
            status=Delivery.STATUS_PENDING,
            scheduled_date=today,
            route__isnull=True,
        )
        .select_related("member", "volunteer", "meal_plan__kitchen")
        .order_by("id")
    )
    return render(
        request,
        "dashboards/admin/attention_unassigned_deliveries.html",
        {
            "page_title": "Unassigned deliveries today",
            "deliveries": deliveries,
            "today": today,
            "active": "home",
        },
    )


@role_required("admin")
def admin_fs_failures_recent(request):
    """Food-safety checks that failed in the last 24 hours.

    Mirrors ``admin_summary._count_fs_failures_24h``.
    """
    from apps.food_safety.models import FoodSafetyCheck

    since = timezone.now() - timedelta(hours=24)
    checks = (
        FoodSafetyCheck.objects
        .filter(result=FoodSafetyCheck.Result.FAIL, checked_at__gte=since)
        .select_related("kitchen", "checked_by")
        .order_by("-checked_at", "-id")
    )
    return render(
        request,
        "dashboards/admin/attention_fs_failures.html",
        {
            "page_title": "Recent food-safety failures",
            "checks": checks,
            "since": since,
            "active": "home",
        },
    )
