"""URL config for the donations app.

Mounted at the project root in ``config/urls.py`` so the Stripe webhook
URL stays at ``/stripe/webhook/`` (Stripe configures the endpoint URL
in their dashboard, not via our router). Other routes carry their own
``donations/`` prefix inside this module to keep the namespace single-
rooted under ``donations:``.

Reverse names:
    * ``donations:stripe_webhook`` — Story 5.4 webhook endpoint.
    * ``donations:impact``         — Story 5.6 donor-impact preview.

Future Story 5.3 / 5.5 / 5.7 routes (donate page, thanks page, manage
page) append below — keep this module additive and group routes by
story for easy auditing.
"""
from django.urls import path

from apps.donations.views import impact_view, stripe_webhook

app_name = "donations"

urlpatterns = [
    # Story 5.4 — Stripe Checkout webhook. Stripe POSTs signed event
    # payloads here; the view verifies the signature, dispatches to
    # ``apps.donations.services.payments``, and is idempotent on re-fire.
    path("stripe/webhook/", stripe_webhook, name="stripe_webhook"),
    # Story 5.6 — "$50 = 16 meals" preview. ``?amount_cents=<int>``.
    path("donations/impact/", impact_view, name="impact"),
]
