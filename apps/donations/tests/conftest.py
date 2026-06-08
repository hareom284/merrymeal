"""Shared pytest fixtures for ``apps/donations/tests``.

The Story 5.4 tests need to patch attributes on the ``stripe`` SDK
(``stripe.checkout.Session.create``, ``stripe.Webhook.construct_event``,
and the ``stripe.error.SignatureVerificationError`` exception class).

The MerryMeal dev / CI environment intentionally does **not** install the
``stripe`` wheel — see ``requirements.txt`` and CLAUDE.md's notes on the
Twilio pattern. So before any test module imports the donations
services / views (which defer ``import stripe`` to call-time), we install
a minimal stub into ``sys.modules`` so:

* ``unittest.mock.patch("stripe.checkout.Session.create", …)`` finds an
  attribute to replace.
* ``except stripe.error.SignatureVerificationError`` in the webhook view
  catches the same exception class the tests raise.

The stub is intentionally dumb — every method either returns ``None`` or
gets monkey-patched by the test itself. Production runs with the real
``stripe`` package and never imports this module.
"""

from __future__ import annotations

import sys
import types

import pytest


def _install_stripe_stub() -> None:
    """Register a minimal fake ``stripe`` package in ``sys.modules``.

    Idempotent — if the real SDK is installed (or a previous test run
    already registered the stub) we leave it alone.
    """
    if "stripe" in sys.modules:
        return

    stripe = types.ModuleType("stripe")
    stripe.api_key = None  # type: ignore[attr-defined]

    # stripe.checkout.Session.create — tests patch the *attribute*.
    checkout = types.ModuleType("stripe.checkout")

    class _Session:
        @staticmethod
        def create(**kwargs):  # pragma: no cover - always patched
            raise RuntimeError(
                "stripe.checkout.Session.create called without a test patch."
            )

    checkout.Session = _Session  # type: ignore[attr-defined]
    stripe.checkout = checkout  # type: ignore[attr-defined]

    # stripe.Webhook.construct_event — tests patch the *attribute*.
    class _Webhook:
        @staticmethod
        def construct_event(payload, sig_header, secret):  # pragma: no cover
            raise RuntimeError(
                "stripe.Webhook.construct_event called without a test patch."
            )

    stripe.Webhook = _Webhook  # type: ignore[attr-defined]

    # stripe.Subscription.delete — Story 5.7 cancel-subscription path.
    # Tests patch ``stripe.Subscription.delete``; production code calls
    # ``stripe.Subscription.delete(sub_id)`` to cancel a recurring gift.
    class _Subscription:
        @staticmethod
        def delete(subscription_id, **kwargs):  # pragma: no cover
            raise RuntimeError(
                "stripe.Subscription.delete called without a test patch."
            )

    stripe.Subscription = _Subscription  # type: ignore[attr-defined]

    # stripe.error.SignatureVerificationError — webhook view catches this.
    error_mod = types.ModuleType("stripe.error")

    class SignatureVerificationError(Exception):
        """Stand-in for the real ``stripe.error.SignatureVerificationError``."""

    error_mod.SignatureVerificationError = SignatureVerificationError  # type: ignore[attr-defined]
    stripe.error = error_mod  # type: ignore[attr-defined]

    sys.modules["stripe"] = stripe
    sys.modules["stripe.checkout"] = checkout
    sys.modules["stripe.error"] = error_mod


# Install the stub at *import* time — before any test module loads the
# donations views / services. This must run before pytest collects
# ``test_stripe_service.py`` / ``test_stripe_webhook.py``.
_install_stripe_stub()


@pytest.fixture
def stripe_session_stub():
    """Mimics ``stripe.checkout.Session.create`` return value.

    The donations service returns ``session.url`` from the SDK, so the
    test only needs an object with ``id`` and ``url`` attributes.
    """

    class _Sess:
        id = "cs_test_123"
        url = "https://checkout.stripe.com/c/pay/cs_test_123"

    return _Sess()
