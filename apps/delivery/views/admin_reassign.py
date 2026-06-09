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
        form = ReassignForm(exclude_volunteer_id=delivery.volunteer_id)
        return _render_modal(request, delivery, form)

    form = ReassignForm(request.POST, exclude_volunteer_id=delivery.volunteer_id)
    if not form.is_valid():
        # Wrong volunteer id, missing field, etc. Re-render the modal
        # with the field errors so the admin sees why save didn't take
        # — silently returning 400 just made the modal look frozen.
        return _render_modal(request, delivery, form, status=400)

    try:
        reassign_delivery(
            delivery, new_volunteer=form.cleaned_data["volunteer"]
        )
    except ValueError as exc:
        # Business-rule failure (route at cap, etc). Surface it in the
        # modal as a top-level error so the admin can pick a different
        # volunteer instead of seeing a dead Save button.
        form.add_error(None, str(exc))
        return _render_modal(request, delivery, form, status=400)

    delivery.refresh_from_db()
    resp = render(
        request, "delivery/admin/_row.html", {"delivery": delivery}
    )
    resp["HX-Trigger"] = "closeModal"
    return resp


def _render_modal(request, delivery, form, *, status: int = 200):
    """Render the reassign modal partial. Used by both GET and the
    error-path of POST so the same template renders every state.

    When called from the POST error path, send ``HX-Retarget`` so HTMX
    swaps the modal slot (showing errors) instead of trying to drop
    the modal HTML into the delivery-row table cell — the success
    swap-target points at the row, which is correct for success and
    very wrong for an error re-render.
    """
    response = render(
        request,
        "delivery/admin/_reassign_modal.html",
        {"delivery": delivery, "form": form},
    )
    if status != 200:
        response["HX-Retarget"] = "#modal-slot"
        response["HX-Reswap"] = "innerHTML"
    response.status_code = status
    return response
