"""Tests for the Anthropic Messages API wrapper.

Every test mocks ``requests.post`` so the suite never touches the real
upstream — running tests with no ANTHROPIC_API_KEY (the default) must
still pass cleanly.
"""
from unittest.mock import MagicMock, patch

import pytest
import requests
from django.test import override_settings

from apps.ai_assistant.services.client import ClaudeUnavailable, generate


def test_generate_raises_when_api_key_missing():
    with override_settings(ANTHROPIC_API_KEY=""):
        with pytest.raises(ClaudeUnavailable, match="not set"):
            generate("system", "hi")


def test_generate_raises_on_wrong_key_format():
    """A Gemini key, OpenAI key, or bearer token must be rejected up
    front — the upstream would 401 anyway, but failing locally gives a
    clearer log message."""
    with override_settings(ANTHROPIC_API_KEY="AIzaWrongVendor"):
        with pytest.raises(ClaudeUnavailable, match="wrong key format"):
            generate("system", "hi")


@patch("apps.ai_assistant.services.client.requests.post")
def test_generate_returns_text_from_content_block(mock_post):
    mock_post.return_value = MagicMock(
        status_code=200,
        raise_for_status=MagicMock(),
        json=lambda: {
            "id": "msg_01",
            "type": "message",
            "role": "assistant",
            "model": "claude-haiku-4-5",
            "stop_reason": "end_turn",
            "content": [
                {"type": "text", "text": "Today's meal is roast chicken."}
            ],
        },
    )
    with override_settings(ANTHROPIC_API_KEY="sk-ant-test"):
        result = generate("system", "what is my meal?")
    assert result == "Today's meal is roast chicken."

    # Confirm we hit the right endpoint with the key + version headers.
    call = mock_post.call_args
    assert call.args[0] == "https://api.anthropic.com/v1/messages"
    assert call.kwargs["headers"]["x-api-key"] == "sk-ant-test"
    assert call.kwargs["headers"]["anthropic-version"] == "2023-06-01"
    assert call.kwargs["headers"]["Content-Type"] == "application/json"

    # System prompt is sent as the top-level ``system`` field, not as
    # a message — the Messages API treats it specially.
    payload = call.kwargs["json"]
    assert payload["system"] == "system"
    assert payload["messages"] == [
        {"role": "user", "content": "what is my meal?"}
    ]


@patch("apps.ai_assistant.services.client.requests.post")
def test_generate_passes_history_with_correct_roles(mock_post):
    """History entries with role ``"assistant"`` or the legacy
    ``"model"`` (left over from the Gemini era) must both reach
    Anthropic as ``"assistant"``."""
    mock_post.return_value = MagicMock(
        status_code=200,
        raise_for_status=MagicMock(),
        json=lambda: {
            "content": [{"type": "text", "text": "ok"}],
            "stop_reason": "end_turn",
        },
    )
    history = [
        {"role": "user", "text": "what's today?"},
        {"role": "model", "text": "Chicken pie."},  # legacy role name
        {"role": "user", "text": "and tomorrow?"},
        {"role": "assistant", "text": "Beef stew."},  # current role name
    ]
    with override_settings(ANTHROPIC_API_KEY="sk-ant-test"):
        generate("system", "follow up?", history=history)

    payload = mock_post.call_args.kwargs["json"]
    assert payload["messages"] == [
        {"role": "user", "content": "what's today?"},
        {"role": "assistant", "content": "Chicken pie."},
        {"role": "user", "content": "and tomorrow?"},
        {"role": "assistant", "content": "Beef stew."},
        {"role": "user", "content": "follow up?"},
    ]


@patch("apps.ai_assistant.services.client.requests.post")
def test_generate_wraps_network_error_as_unavailable(mock_post):
    mock_post.side_effect = requests.ConnectionError("timeout")
    with override_settings(ANTHROPIC_API_KEY="sk-ant-test"):
        with pytest.raises(ClaudeUnavailable, match="network"):
            generate("system", "hi")


@patch("apps.ai_assistant.services.client.requests.post")
def test_generate_wraps_http_error_as_unavailable(mock_post):
    """A 401 from a bad/revoked key must surface as ClaudeUnavailable
    so the view shows the static fallback instead of a 500."""
    http_error = requests.HTTPError("401 Unauthorized")
    http_error.response = MagicMock(status_code=401, text="authentication_error")
    mock_post.return_value = MagicMock(
        status_code=401,
        raise_for_status=MagicMock(side_effect=http_error),
    )
    with override_settings(ANTHROPIC_API_KEY="sk-ant-test"):
        with pytest.raises(ClaudeUnavailable, match="http 401"):
            generate("system", "hi")


@patch("apps.ai_assistant.services.client.requests.post")
def test_generate_wraps_empty_response_as_unavailable(mock_post):
    """A refusal / safety stop comes back with no usable text. The
    member must never see a blank bubble — fall back instead."""
    mock_post.return_value = MagicMock(
        status_code=200,
        raise_for_status=MagicMock(),
        json=lambda: {
            "content": [],
            "stop_reason": "refusal",
        },
    )
    with override_settings(ANTHROPIC_API_KEY="sk-ant-test"):
        with pytest.raises(ClaudeUnavailable, match="empty response"):
            generate("system", "anything")
