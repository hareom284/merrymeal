"""Test-only helpers shared across apps.

The :data:`sms_outbox` mirrors :data:`django.core.mail.outbox` for SMS.
The ``console`` SMS backend (``apps.core.services.sms_backends``) appends
to this list so tests can assert on outbound text messages without ever
hitting the network. Production code MUST NOT import from this module.
"""
from __future__ import annotations

#: In-memory list of dicts ``{"to": str, "body": str}`` populated by the
#: console SMS backend. Tests should ``.clear()`` it between cases.
sms_outbox: list[dict] = []
