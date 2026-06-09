"""View: member tracking-status polling endpoint (Story 4.12).

Thin glue: scopes the ``Delivery`` queryset to "delivery the viewer is
allowed to see", delegates to ``get_tracking_context``, and renders the
partial. The same partial is also include-d from the member home today
card, so a non-HTMX page load (initial render) and an HTMX poll both
hit the exact same template — no branching on the ``HX-Request`` header.

Allowed viewers:
* the **member** who owns the delivery (``Delivery.member``),
* a **caregiver** linked to that member through
  ``accounts.CaregiverLink`` (``member_caregivers`` table). The reverse
  relation on ``User.member`` is ``caregiver_links_as_member`` (see
  ``apps/accounts/models/caregiver_links.py``) — the spec's
  ``member__caregivers__caregiver`` lookup does not exist in this
  schema, so we use the actual related name.

Everyone else — admins, kitchen staff, other members — sees a 404.
Hiding behind 404 (rather than 403) keeps delivery IDs unenumerable.
"""
from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from apps.delivery.models import Delivery
from apps.delivery.services.tracking import get_tracking_context


@login_required
def tracking_status_view(request, pk: int):
    user = request.user
    role = getattr(user, "role", None)

    qs = Delivery.objects.select_related("volunteer", "member").filter(pk=pk)
    if role == "member":
        qs = qs.filter(member=user)
    elif role == "caregiver":
        qs = qs.filter(member__caregiver_links_as_member__caregiver=user)
    else:
        qs = qs.none()

    delivery = get_object_or_404(qs)

    # Direct browser visit (no ``HX-Request`` header) → redirect to the
    # full ``/track/`` page so the user sees the app shell + map +
    # progress timeline instead of a bare partial on a blank screen.
    # HTMX polls still get the partial they expect.
    if request.headers.get("HX-Request") != "true":
        return redirect(reverse("delivery:member_track"))

    context = get_tracking_context(delivery, user)
    return render(request, "delivery/member/_tracking_card.html", context)
