"""Story 5.7 — sign / verify roundtrip for the magic-link tokens.

These tests pin three guarantees the manage-link flow relies on:

* **Roundtrip** — a freshly issued token decodes back to the same email
  and creates a matching ``MagicLinkToken`` row.
* **Expiry** — a token older than 30 minutes raises
  ``SignatureExpired``. We simulate the clock by monkey-patching
  ``django.core.signing.time.time`` rather than pulling in ``freezegun``
  (which is not on the project's pinned dependency list — see
  ``apps/planning/tests/test_validate_command.py`` for the same idiom).
* **Single-use** — a second ``verify_token(..., mark_used=True)`` call
  with the same token raises ``BadSignature`` because the
  ``MagicLinkToken.used_at`` flag has already flipped.
* **Tamper resistance** — appending junk to the signed string breaks
  the signature and raises ``BadSignature``.
"""

from __future__ import annotations

import time as _time

import pytest
from django.core.signing import BadSignature, SignatureExpired

from apps.donations.models import MagicLinkToken
from apps.donations.services.manage import issue_token, verify_token


@pytest.mark.django_db
def test_issue_and_verify_roundtrip():
    token = issue_token("a@x.com")
    payload = verify_token(token)
    assert payload["email"] == "a@x.com"
    assert MagicLinkToken.objects.filter(token_id=payload["tid"]).exists()


@pytest.mark.django_db
def test_token_expires_after_30_minutes(monkeypatch):
    """Token older than ``max_age=1800`` raises ``SignatureExpired``.

    ``django.core.signing`` stamps the token with the current Unix
    timestamp (``time.time()``) and ``loads`` re-reads it the same way.
    Monkey-patching ``time.time`` inside the ``django.core.signing``
    namespace makes the token *look* 31 minutes old to the verifier
    without touching system time or pulling in ``freezegun``.
    """
    token = issue_token("a@x.com")
    from django.core import signing as _signing

    fake_now = _time.time() + 31 * 60  # 31 minutes in the future
    monkeypatch.setattr(_signing.time, "time", lambda: fake_now)
    with pytest.raises(SignatureExpired):
        verify_token(token)


@pytest.mark.django_db
def test_token_is_single_use():
    token = issue_token("a@x.com")
    verify_token(token, mark_used=True)
    with pytest.raises(BadSignature):
        verify_token(token, mark_used=True)


@pytest.mark.django_db
def test_tampered_token_rejected():
    token = issue_token("a@x.com")
    with pytest.raises(BadSignature):
        verify_token(token + "junk")
