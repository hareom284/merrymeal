"""Story 5.5 — thank-you page shown after the Stripe Checkout redirect.

Stripe sends the donor back to ``/donate/thanks/?session_id=<sid>`` once
the Checkout session completes (the ``DONATIONS_SUCCESS_URL`` setting in
:mod:`config.settings.base` configures this). The webhook race usually
resolves in our favour — by the time the browser follows the redirect,
``apps.donations.services.payments.apply_checkout_completed`` has
already flipped the ``Donation`` to ``completed`` and stamped a
``receipt_number``.

When the race goes the other way (no webhook yet, donation still
``pending``, or the session id isn't ours), we render a soft
"processing" page instead of 404ing on the donor — Stripe almost always
catches up within seconds, and forcing the donor to wonder if their
card was charged is bad UX.

The view is **public** (no auth). Anyone who happens to type the URL
sees the same soft state — no donation metadata leaks because we filter
by ``status="completed"`` on a specific ``transaction_id``.
"""
from __future__ import annotations

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET

from apps.donations.models import Donation
from apps.donations.services.impact import meals_for_amount


@require_GET
def thanks_page(request: HttpRequest) -> HttpResponse:
    """Render the thank-you page for a completed donation.

    Looks up the donation by ``?session_id=<sid>`` against
    ``transaction_id`` AND ``status="completed"``. If either is missing
    or no match exists, the template falls back to the processing-state
    branch. ``meals`` is the same ``meals_for_amount`` figure the
    receipt email and impact preview show.
    """
    session_id = request.GET.get("session_id", "")
    donation = None
    if session_id:
        donation = (
            Donation.objects
            .filter(transaction_id=session_id, status="completed")
            .select_related("campaign")
            .first()
        )

    meals = meals_for_amount(donation.amount_cents) if donation else 0

    return render(
        request,
        "donations/thanks.html",
        {
            "donation": donation,
            "meals": meals,
        },
    )
