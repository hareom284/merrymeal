"""View: 2-tap meal feedback POST endpoint (Story 4.11).

HTMX endpoint reachable only by a logged-in user with ``role='member'``.
The path PK is the ``Delivery.id`` — we re-scope it to the
``request.user`` so a foreign or missing PK returns 404 (NOT 403),
which keeps delivery IDs unenumerable.

Status guards:
* delivery must already be ``delivered`` — rating a pending stop is
  meaningless and would skew Epic 06 reporting (returns 400).
* one feedback row per delivery — the duplicate-submit path returns
  200 + the "already recorded" thanks partial so HTMX can swap it into
  place without the member seeing an error.

The view itself only validates the form and orchestrates the
re-render; the side-effect (insert + idempotent retry on race) lives in
``apps.delivery.services.feedback.record_feedback``.
"""
from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST

from apps.core.decorators import role_required
from apps.delivery.forms.feedback import FeedbackForm
from apps.delivery.models import Delivery, DeliveryFeedback
from apps.delivery.services.feedback import record_feedback


@login_required
@role_required("member")
@require_POST
def feedback_view(request, pk: int):
    """POST handler for `/member/feedback/<pk>/`.

    HTMX target: `#feedback-card-<pk>` (the wrapper rendered by
    ``_feedback_card.html``). We always return either the thanks
    partial (success or duplicate) or a bare 400/404 — never a full
    page — so the swap behaviour is consistent.
    """
    delivery = get_object_or_404(
        Delivery, pk=pk, member=request.user,
    )

    if delivery.status != Delivery.STATUS_DELIVERED:
        return HttpResponse(status=400)

    if DeliveryFeedback.objects.filter(delivery=delivery).exists():
        return render(
            request,
            "delivery/member/_feedback_thanks.html",
            {"already": True},
            status=200,
        )

    form = FeedbackForm(request.POST)
    if not form.is_valid():
        return HttpResponse(status=400)

    record_feedback(
        delivery,
        rating=form.cleaned_data["rating"],
        tags=form.cleaned_data["tags"],
    )
    return render(
        request,
        "delivery/member/_feedback_thanks.html",
        {"already": False},
    )
