"""Views package for the donations app.

Sub-modules:

* ``checkout`` — Story 5.4 Stripe webhook endpoint.
* ``impact``   — Story 5.6 donor-impact preview.

Re-exports the per-feature view callables so URL configs can
``from apps.donations.views import impact_view`` without reaching into
private modules. Sprint 09 follow-ups (5.3 donate, 5.5 thanks, 5.7
manage) append their own sub-modules and re-exports here.

Story 5.3's public donate page will land in a sibling sub-module
(``donate.py``) — kept separate so the webhook view's ``csrf_exempt``
decorator never accidentally bleeds onto a user-facing form.
"""

from apps.donations.views.checkout import stripe_webhook
from apps.donations.views.impact import impact_view

__all__ = ["impact_view", "stripe_webhook"]
