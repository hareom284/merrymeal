"""Volunteer-facing delivery views.

Story 4.8 introduced ``today_view`` (the route screen).
Story 4.9 adds ``mark_delivered_view`` — the HTMX endpoint the screen
POSTs to when the volunteer presses the sticky CTA. It uploads the POD
photo, flips the delivery to ``delivered``, and returns the re-rendered
route fragment (so HTMX can swap the next stop into the "current"
slot without a full page reload).
"""
from __future__ import annotations

import logging

from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST

from apps.core.decorators import role_required
from apps.delivery.forms import MarkDeliveredForm
from apps.delivery.models import Delivery
from apps.delivery.services.mark_delivered import mark_delivered
from apps.delivery.services.photo import upload_pod_photo
from apps.delivery.services.volunteer_today import get_today_route

logger = logging.getLogger("merrymeal.pod")


@login_required
@role_required("volunteer")
def today_view(request):
    context = get_today_route(request.user)
    return render(request, "delivery/volunteer/today.html", context)


@login_required
@role_required("volunteer")
@require_POST
def mark_delivered_view(request, pk: int):
    """HTMX endpoint: upload POD photo + flip the delivery to ``delivered``.

    Scope: the row must belong to ``request.user``. A foreign or
    missing pk → 404 (NOT 403). 403 would leak that the row exists —
    spec acceptance criterion.
    """
    try:
        delivery = get_object_or_404(
            Delivery, pk=pk, volunteer=request.user
        )
    except Http404:
        raise

    form = MarkDeliveredForm(request.POST, request.FILES)
    if not form.is_valid():
        return HttpResponse(status=400)

    photo_url = upload_pod_photo(
        form.cleaned_data["photo"], delivery_id=delivery.id
    )
    mark_delivered(
        delivery,
        photo_url=photo_url,
        lat=form.cleaned_data.get("latitude"),
        lng=form.cleaned_data.get("longitude"),
    )

    # Structured log line so we can reconcile against the client's
    # localStorage queue when chasing "did this delivery actually land?"
    # support tickets (mitigates Sprint 08 risk: "offline queue eats a
    # delivery").
    logger.info(
        "pod.delivered delivery=%s volunteer=%s",
        delivery.id,
        request.user.id,
    )

    context = get_today_route(request.user)
    return render(
        request, "delivery/volunteer/_route_fragment.html", context
    )
