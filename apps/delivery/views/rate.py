"""Standalone rate-meal page (Story 12.8).

Wraps the existing 4.11 feedback partial in a full-page chrome so the
"How was lunch yesterday?" notification (12.6) has somewhere to link,
and so members on slow connections (where the inline HTMX swap on the
dashboard feels unreliable) get a dedicated screen.

POST to ``/member/feedback/<pk>/`` still owns the side effect — this
view is render-only.
"""
from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import get_object_or_404, render

from apps.core.decorators import role_required
from apps.delivery.forms.feedback import TAG_CHOICES
from apps.delivery.models import Delivery, DeliveryFeedback


@login_required
@role_required("member")
def rate_meal_view(request, delivery_id: int):
    """GET ``/rate/<delivery_id>/``. Renders the same feedback form the
    dashboard uses, plus a meal-info header so the page stands on its own.
    The submit POST still goes to ``delivery:feedback`` — this view is
    presentation only.
    """
    delivery = get_object_or_404(
        Delivery.objects.select_related("meal_plan__meal", "volunteer"),
        pk=delivery_id,
        member=request.user,
    )
    if delivery.status != Delivery.STATUS_DELIVERED:
        # Rating a pending stop is meaningless; 404 keeps delivery IDs
        # unenumerable (same convention as the POST endpoint).
        raise Http404("This delivery cannot be rated yet.")

    already_rated = DeliveryFeedback.objects.filter(delivery=delivery).exists()

    return render(
        request,
        "delivery/member/rate.html",
        {
            "active": "dashboard",
            "page_title": "Rate your meal",
            "delivery": delivery,
            "meal": delivery.meal_plan.meal,
            "tag_choices": TAG_CHOICES,
            "already_rated": already_rated,
        },
    )
