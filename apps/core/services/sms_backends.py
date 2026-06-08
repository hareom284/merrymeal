"""SMS backend implementations.

The console backend is used in dev and test; it captures messages in the
in-memory :data:`apps.core.testing.sms_outbox` so assertions stay fast
and offline. The Twilio backend is the prod transport — it is **only**
imported when ``settings.SMS_BACKEND == "twilio"`` because the ``twilio``
package is not installed on dev / CI machines.
"""
from __future__ import annotations

from django.conf import settings

from apps.core.testing import sms_outbox


class ConsoleBackend:
    """Append outbound SMS to :data:`sms_outbox` and echo to stdout.

    The echo is helpful when a developer runs ``manage.py runserver`` and
    wants to eyeball the body without opening the test outbox.
    """

    def send(self, *, to: str, body: str) -> None:
        sms_outbox.append({"to": to, "body": body})
        print(f"[sms] -> {to}: {body}")


class TwilioBackend:
    """Real-world transport. One outbound REST call per recipient.

    The ``twilio`` import lives **inside** ``send()`` so dev environments
    that do not install the package can still import this module (the
    facade in :mod:`apps.core.services.sms` references both backends by
    class). Catching ``TwilioRestException`` is left to the caller / the
    django-q2 task wrapper so retry behaviour is uniform with the rest
    of the queue.
    """

    def send(self, *, to: str, body: str) -> None:
        from twilio.rest import Client

        client = Client(
            settings.TWILIO_ACCOUNT_SID,
            settings.TWILIO_AUTH_TOKEN,
        )
        client.messages.create(
            to=to,
            body=body,
            from_=settings.TWILIO_FROM,
        )
