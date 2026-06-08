"""URL config for the donations app.

Mounted at the project root in ``config/urls.py``. The Story 5.4
webhook lives at ``/stripe/webhook/`` (un-prefixed because Stripe
configures the endpoint URL in their dashboard, not via our router).

Reverse names:
    * ``donations:stripe_webhook`` — Story 5.4

Future Story 5.3 / 5.5 / 5.6 / 5.7 routes (donate page, thanks page,
campaign progress widget, manage page) append to ``urlpatterns`` below
under the ``donate/`` and ``donations/`` prefixes.
"""
from django.urls import path

from apps.donations.views.checkout import stripe_webhook

app_name = "donations"

urlpatterns = [
    # Story 5.4 — Stripe Checkout webhook. Stripe POSTs signed event
    # payloads here; the view verifies the signature, dispatches to
    # ``apps.donations.services.payments``, and is idempotent on re-fire.
    path("stripe/webhook/", stripe_webhook, name="stripe_webhook"),
]
