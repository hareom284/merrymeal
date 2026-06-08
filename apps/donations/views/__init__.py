"""Views package for the donations app.

Sub-modules:

* ``donate``   — Story 5.3 public donate page (GET + POST).
* ``checkout`` — Story 5.4 Stripe webhook endpoint.
* ``impact``   — Story 5.6 donor-impact preview.
* ``manage``   — Story 5.7 recurring-donation magic-link manage page.

Re-exports the per-feature view callables so URL configs can
``from apps.donations.views import donate_page`` without reaching into
private modules.

The donate page (``donate.py``) is kept in a separate sub-module from
the webhook view (``checkout.py``) so the webhook's ``csrf_exempt``
decorator never accidentally bleeds onto a user-facing form.
"""

from apps.donations.views.checkout import stripe_webhook
from apps.donations.views.donate import donate_page, donate_start
from apps.donations.views.impact import impact_view
from apps.donations.views.manage import (
    manage_request_sent_view,
    manage_request_view,
    manage_view,
)
from apps.donations.views.thanks import thanks_page

__all__ = [
    "donate_page",
    "donate_start",
    "impact_view",
    "manage_request_sent_view",
    "manage_request_view",
    "manage_view",
    "stripe_webhook",
    "thanks_page",
]
