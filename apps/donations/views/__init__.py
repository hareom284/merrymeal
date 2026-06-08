"""Views package for the donations app.

Sub-modules:

* ``donate``   — Story 5.3 public donate page (GET + POST).
* ``checkout`` — Story 5.4 Stripe webhook endpoint.
* ``impact``   — Story 5.6 donor-impact preview.

Re-exports the per-feature view callables so URL configs can
``from apps.donations.views import donate_page`` without reaching into
private modules. Sprint 09 follow-ups (5.5 thanks, 5.7 manage) append
their own sub-modules and re-exports here.

The donate page (``donate.py``) is kept in a separate sub-module from
the webhook view (``checkout.py``) so the webhook's ``csrf_exempt``
decorator never accidentally bleeds onto a user-facing form.
"""

from apps.donations.views.checkout import stripe_webhook
from apps.donations.views.donate import donate_page, donate_start
from apps.donations.views.impact import impact_view

__all__ = [
    "donate_page",
    "donate_start",
    "impact_view",
    "stripe_webhook",
]
