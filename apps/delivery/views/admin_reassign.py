"""Story 4.14 — modal GET + POST endpoint for reassigning a delivery.

GET  — renders the modal partial with the volunteer dropdown.
POST — runs ``reassign_delivery`` and returns the updated row partial,
       with an ``HX-Trigger: closeModal`` header so the JS listener in
       the modal partial knows to clear the slot.
"""
from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_http_methods

from apps.core.decorators import role_required
from apps.delivery.forms.reassign import ReassignForm
from apps.delivery.models import Delivery
from apps.delivery.services.reassign import reassign_delivery


@login_required
@role_required("admin")
@require_http_methods(["GET", "POST"])
def reassign_view(request, pk: int):
    delivery = get_object_or_404(Delivery, pk=pk)

    if request.method == "GET":
        form = ReassignForm()
        return render(
            request,
            "delivery/admin/_reassign_modal.html",
            {"delivery": delivery, "form": form},
        )

    form = ReassignForm(request.POST)
    if not form.is_valid():
        # Wrong volunteer id, missing field, etc. The dropdown's
        # queryset already excludes non-volunteers, so this is the
        # path for "tried to pick a non-volunteer".
        return HttpResponse("invalid volunteer", status=400)

    try:
        reassign_delivery(
            delivery, new_volunteer=form.cleaned_data["volunteer"]
        )
    except ValueError as exc:
        return HttpResponse(str(exc), status=400)

    delivery.refresh_from_db()
    resp = render(
        request, "delivery/admin/_row.html", {"delivery": delivery}
    )
    resp["HX-Trigger"] = "closeModal"
    return resp
