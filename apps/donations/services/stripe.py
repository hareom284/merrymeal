"""Stub Stripe service — Story 5.4 replaces this with the real Checkout call.

The public donate page (Story 5.3) needs *something* to redirect to so the
flow tests pass end-to-end, but the actual Stripe integration (API key,
session creation, webhook handler) is the next story's job. Until then this
returns a deterministic placeholder URL so view tests can assert on it
without booting Stripe.

When 5.4 lands, replace ``create_checkout_session`` with the real
``stripe.checkout.Session.create(...)`` call — the signature stays the same
so callers (``start_donation``) don't change.
"""

from __future__ import annotations


def create_checkout_session(donation_id: int, *, recurring: bool) -> str:
    """Return a placeholder Stripe Checkout URL.

    The ``recurring`` kwarg is unused in the stub but kept on the signature
    so Story 5.4's swap-in is purely additive (subscription mode vs one-off
    payment mode).
    """
    # ``recurring`` will branch on ``mode=subscription`` vs ``mode=payment``
    # once the real Stripe call lands — for now both paths share the stub.
    del recurring
    return f"https://stripe.test/sess_stub_{donation_id}"
