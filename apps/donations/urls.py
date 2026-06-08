"""URL config for the donations app.

Mounted at the project root in ``config/urls.py`` so the Stripe webhook
URL stays at ``/stripe/webhook/`` (Stripe configures the endpoint URL
in their dashboard, not via our router). Other routes carry their own
``donate/`` and ``donations/`` prefixes inside this module to keep the
namespace single-rooted under ``donations:``.

Reverse names:
    * ``donations:donate``              — Story 5.3 public donate page (GET).
    * ``donations:donate_start``        — Story 5.3 donate-page POST.
    * ``donations:stripe_webhook``      — Story 5.4 webhook endpoint.
    * ``donations:thanks``              — Story 5.5 post-Stripe-redirect page.
    * ``donations:impact``              — Story 5.6 donor-impact preview.
    * ``donations:manage_request``      — Story 5.7 email-entry form.
    * ``donations:manage_request_sent`` — Story 5.7 "check your inbox" page.
    * ``donations:manage``              — Story 5.7 magic-link landing.
"""
from django.urls import path

from apps.donations.views import (
    donate_page,
    donate_start,
    impact_view,
    manage_request_sent_view,
    manage_request_view,
    manage_view,
    stripe_webhook,
    thanks_page,
)

app_name = "donations"

urlpatterns = [
    # Story 5.3 — public donate page (no login required). GET renders
    # the hero + amount chips; POST goes through donate_start to create
    # the pending Donation and hand off to Stripe Checkout.
    path("donate/", donate_page, name="donate"),
    path("donate/start/", donate_start, name="donate_start"),
    # Story 5.5 — thank-you page Stripe redirects to after a successful
    # Checkout session. Path is wired to ``DONATIONS_SUCCESS_URL`` in
    # ``config/settings/base.py``; the session id arrives as
    # ``?session_id={CHECKOUT_SESSION_ID}``.
    path("donate/thanks/", thanks_page, name="thanks"),
    # Story 5.4 — Stripe Checkout webhook. Stripe POSTs signed event
    # payloads here; the view verifies the signature, dispatches to
    # ``apps.donations.services.payments``, and is idempotent on re-fire.
    path("stripe/webhook/", stripe_webhook, name="stripe_webhook"),
    # Story 5.6 — "$50 = 16 meals" preview. ``?amount_cents=<int>``.
    path("donations/impact/", impact_view, name="impact"),
    # Story 5.7 — recurring-donation magic-link management.
    # Order matters: the literal ``sent/`` route MUST come before the
    # ``<str:token>/`` catch-all, or Django would treat "sent" as a
    # signed token (and 410 every donor on the success page).
    path("donate/manage/", manage_request_view, name="manage_request"),
    path(
        "donate/manage/sent/",
        manage_request_sent_view,
        name="manage_request_sent",
    ),
    path("donate/manage/<str:token>/", manage_view, name="manage"),
]
