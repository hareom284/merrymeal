"""Tests for the rate limiter + its integration with the chat views."""
from unittest.mock import patch

import pytest
from django.core.cache import cache
from django.test import override_settings

from apps.accounts.tests.factories import UserFactory
from apps.ai_assistant.services.rate_limit import check


@pytest.fixture(autouse=True)
def _clear_cache():
    """Each test starts with a clean cache so the bucket counters don't
    leak between cases."""
    cache.clear()
    yield
    cache.clear()


# ---- service ---------------------------------------------------------

def test_under_limit_allowed():
    with override_settings(
        GEMINI_RATE_LIMIT_PER_USER=5,
        GEMINI_RATE_LIMIT_GLOBAL=100,
    ):
        for i in range(5):
            assert check(user_id=42).allowed, f"hit {i + 1} should still be allowed"


def test_per_user_trip():
    with override_settings(
        GEMINI_RATE_LIMIT_PER_USER=3,
        GEMINI_RATE_LIMIT_GLOBAL=100,
    ):
        for _ in range(3):
            assert check(user_id=42).allowed
        verdict = check(user_id=42)
        assert not verdict.allowed
        assert verdict.scope == "user"
        assert 0 < verdict.retry_after <= 60


def test_per_user_isolates_users():
    """Tripping user A must not lock out user B."""
    with override_settings(
        GEMINI_RATE_LIMIT_PER_USER=2,
        GEMINI_RATE_LIMIT_GLOBAL=100,
    ):
        for _ in range(2):
            check(user_id=1)
        assert not check(user_id=1).allowed
        assert check(user_id=2).allowed


def test_global_trip():
    """Once the project-wide cap is hit, every user gets a 'global' verdict."""
    with override_settings(
        GEMINI_RATE_LIMIT_PER_USER=100,
        GEMINI_RATE_LIMIT_GLOBAL=3,
    ):
        # Spread hits across users so the per-user cap doesn't fire first.
        for uid in (1, 2, 3):
            assert check(user_id=uid).allowed
        verdict = check(user_id=4)
        assert not verdict.allowed
        assert verdict.scope == "global"


# ---- view integration ------------------------------------------------

@pytest.mark.django_db
@patch("apps.ai_assistant.services.chat.generate")
def test_chat_renders_soft_rate_limit_reply(mock_generate, client):
    """Tripping the per-user limit must NOT 500 or block the widget —
    the view renders the standard ``_exchange.html`` partial with a
    soft "wait N seconds" body so the conversation can continue."""
    mock_generate.return_value = "ok"
    user = UserFactory(role="member")
    client.force_login(user)

    with override_settings(
        GEMINI_RATE_LIMIT_PER_USER=2,
        GEMINI_RATE_LIMIT_GLOBAL=100,
    ):
        client.post("/assistant/chat/", {"message": "q1"})
        client.post("/assistant/chat/", {"message": "q2"})
        response = client.post("/assistant/chat/", {"message": "q3"})

    assert response.status_code == 200
    body = response.content
    assert b"going a bit fast" in body
    assert response["Retry-After"]
    # Gemini was called for q1 + q2 only, NOT q3.
    assert mock_generate.call_count == 2


@pytest.mark.django_db
@patch("apps.ai_assistant.services.chat.generate")
def test_global_limit_uses_busy_copy(mock_generate, client):
    """Global trip shows the 'assistant is busy' copy (truthful), not
    the per-user 'going a bit fast' copy."""
    mock_generate.return_value = "ok"
    # Two members to spread hits across user counters.
    a = UserFactory(role="member", email="a@example.com")
    b = UserFactory(role="member", email="b@example.com")

    with override_settings(
        GEMINI_RATE_LIMIT_PER_USER=100,
        GEMINI_RATE_LIMIT_GLOBAL=2,
    ):
        client.force_login(a)
        client.post("/assistant/chat/", {"message": "first"})
        client.force_login(b)
        client.post("/assistant/chat/", {"message": "second"})
        response = client.post("/assistant/chat/", {"message": "third"})

    body = response.content
    assert b"assistant is a bit busy" in body
