"""Story 5.4 — Stripe webhook endpoint.

Routes
------

* ``POST /stripe/webhook/`` (reverse name ``donations:stripe_webhook``)
  Receives signed event callbacks from Stripe and dispatches to the
  payment service functions in :mod:`apps.donations.services.payments`.

Signature verification
----------------------

We call ``stripe.Webhook.construct_event`` with the raw request body,
the ``Stripe-Signature`` header and ``settings.STRIPE_WEBHOOK_SECRET``.
Any failure — bad signature, missing header, malformed JSON — returns
**HTTP 401 with zero DB writes**. Stripe will retry, but we never
trust an unsigned payload.

CSRF
----

Stripe does not send a Django CSRF token. The view is decorated with
``@csrf_exempt`` — the signature header IS our authenticity check. Per
the Story 5.4 reviewer checklist, a missing ``csrf_exempt`` would 403
silently in prod.

Deferred import
---------------

``import stripe`` is deferred to call-time, mirroring the Twilio pattern
in ``apps.core.services.sms_backends.TwilioBackend.send``. Dev / CI
environments do not pip-install the ``stripe`` wheel; tests register a
stub in ``sys.modules`` via ``apps/donations/tests/conftest.py``.
"""

from __future__ import annotations

import logging

from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from apps.donations.services.payments import (
    apply_checkout_completed,
    apply_invoice_paid,
    apply_subscription_deleted,
)

logger = logging.getLogger("merrymeal.donations")


@csrf_exempt
@require_POST
def stripe_webhook(request):
    """Handle a signed Stripe webhook callback.

    Returns:
        * HTTP 401 on bad signature, missing header, or malformed JSON.
        * HTTP 200 ``{"received": true}`` on a recognised event or any
          unknown event type (so Stripe stops retrying).
        * HTTP 500 only if the dispatched handler raises — surfaces
          loudly in Sentry / the django-q2 retry queue.
    """
    # Deferred import — see module docstring.
    import stripe

    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE", "")
    payload = request.body

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET,
        )
    except stripe.error.SignatureVerificationError:
        logger.warning("Stripe webhook rejected: bad signature")
        return HttpResponse(status=401)
    except ValueError:
        # Malformed payload / missing header.
        logger.warning("Stripe webhook rejected: malformed payload")
        return HttpResponse(status=401)

    event_type = event.get("type", "")
    obj = (event.get("data") or {}).get("object") or {}

    if event_type == "checkout.session.completed":
        apply_checkout_completed(obj)
    elif event_type == "invoice.paid":
        apply_invoice_paid(obj)
    elif event_type == "customer.subscription.deleted":
        apply_subscription_deleted(obj)
    else:
        # Unknown / unhandled event types — log and return 200 so
        # Stripe doesn't retry forever. Future stories can subscribe to
        # additional types without changing this dispatch table.
        logger.info("Stripe webhook ignored: %s", event_type)

    return JsonResponse({"received": True})
