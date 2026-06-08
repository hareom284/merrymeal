"""Views package for the donations app.

Sub-modules:

* ``checkout`` — Story 5.4 Stripe webhook endpoint.

Story 5.3's public donate page lands in a sibling sub-module
(``donate.py``) — kept separate so the webhook view's
``csrf_exempt`` decorator never accidentally bleeds onto a user-facing
form.
"""

from apps.donations.views.checkout import stripe_webhook

__all__ = ["stripe_webhook"]
