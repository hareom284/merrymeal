"""SMS facade.

Resolves :setting:`SMS_BACKEND` at call time so tests can flip the
backend per case with ``@override_settings``. Caller-side API mirrors
:func:`django.core.mail.send_mail`: keyword-only ``to`` and ``body``
to make accidental positional misuse loud.
"""
from __future__ import annotations

from django.conf import settings

from apps.core.services.sms_backends import ConsoleBackend, TwilioBackend

#: Registry of available backends. Keep both classes referenced here so
#: a typo in ``SMS_BACKEND`` raises ``ValueError`` instead of silently
#: dropping messages.
BACKENDS = {
    "console": ConsoleBackend,
    "twilio": TwilioBackend,
}


def send_sms(*, to: str, body: str) -> None:
    """Dispatch a single SMS via the configured backend.

    Raises ``ValueError`` if ``settings.SMS_BACKEND`` is not registered.
    """
    name = getattr(settings, "SMS_BACKEND", "console")
    cls = BACKENDS.get(name)
    if cls is None:
        raise ValueError(f"unknown SMS_BACKEND: {name}")
    cls().send(to=to, body=body)
