"""Tests for the Gemini REST wrapper.

Every test mocks ``requests.post`` so the suite never touches the real
upstream — running tests with no GEMINI_API_KEY (the default) must
still pass cleanly.
"""
from unittest.mock import MagicMock, patch

import pytest
import requests
from django.test import override_settings

from apps.ai_assistant.services.client import GeminiUnavailable, generate


def test_generate_raises_when_api_key_missing():
    with override_settings(GEMINI_API_KEY=""):
        with pytest.raises(GeminiUnavailable, match="not set"):
            generate("system", "hi")


@patch("apps.ai_assistant.services.client.requests.post")
def test_generate_returns_text_from_first_candidate(mock_post):
    mock_post.return_value = MagicMock(
        status_code=200,
        raise_for_status=MagicMock(),
        json=lambda: {
            "candidates": [
                {"content": {"parts": [{"text": "Today's meal is roast chicken."}]}}
            ]
        },
    )
    with override_settings(GEMINI_API_KEY="pk.test"):
        result = generate("system", "what is my meal?")
    assert result == "Today's meal is roast chicken."

    # Confirm we hit the right endpoint with the key in the query string.
    call = mock_post.call_args
    assert "generateContent" in call.args[0]
    assert call.kwargs["params"] == {"key": "pk.test"}


@patch("apps.ai_assistant.services.client.requests.post")
def test_generate_wraps_network_error_as_unavailable(mock_post):
    mock_post.side_effect = requests.ConnectionError("timeout")
    with override_settings(GEMINI_API_KEY="pk.test"):
        with pytest.raises(GeminiUnavailable, match="network"):
            generate("system", "hi")


@patch("apps.ai_assistant.services.client.requests.post")
def test_generate_wraps_safety_block_as_unavailable(mock_post):
    """Gemini surfaces safety blocks with no ``candidates`` field. The
    member must never see the raw block reason — fall back instead."""
    mock_post.return_value = MagicMock(
        status_code=200,
        raise_for_status=MagicMock(),
        json=lambda: {"promptFeedback": {"blockReason": "SAFETY"}},
    )
    with override_settings(GEMINI_API_KEY="pk.test"):
        with pytest.raises(GeminiUnavailable, match="empty"):
            generate("system", "anything")
