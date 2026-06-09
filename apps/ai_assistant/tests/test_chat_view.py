"""End-to-end tests for the /assistant/chat/ HTMX endpoint."""
from unittest.mock import patch

import pytest

from apps.accounts.tests.factories import UserFactory
from apps.ai_assistant.services.client import ClaudeUnavailable


@pytest.mark.django_db
def test_chat_requires_login(client):
    response = client.post("/assistant/chat/", {"message": "hi"})
    assert response.status_code == 302
    assert "/login/" in response.url or "/accounts/login/" in response.url


@pytest.mark.django_db
def test_chat_rejects_get(client):
    user = UserFactory(role="member")
    client.force_login(user)
    response = client.get("/assistant/chat/")
    assert response.status_code == 405


@pytest.mark.django_db
def test_chat_empty_message_returns_empty_body(client):
    user = UserFactory(role="member")
    client.force_login(user)
    response = client.post("/assistant/chat/", {"message": "   "})
    assert response.status_code == 200
    # Whitespace-only renders nothing so the log is unchanged.
    assert response.content.strip() == b""


@pytest.mark.django_db
@patch("apps.ai_assistant.services.chat.generate")
def test_chat_renders_user_and_assistant_bubbles(mock_generate, client):
    """Happy path — mock Claude, assert both bubbles are in the partial."""
    mock_generate.return_value = "Today's meal is roast chicken."
    user = UserFactory(role="member")
    client.force_login(user)
    response = client.post(
        "/assistant/chat/", {"message": "what is my meal today?"}
    )
    assert response.status_code == 200
    body = response.content
    assert b"assistant-user-bubble" in body
    assert b"assistant-reply-bubble" in body
    assert b"what is my meal today?" in body
    assert b"Today&#x27;s meal is roast chicken." in body or b"Today's meal is roast chicken." in body


@pytest.mark.django_db
@patch("apps.ai_assistant.services.chat.generate")
def test_chat_falls_back_when_claude_unavailable(mock_generate, client):
    """The widget must NEVER crash — Claude-down returns the static
    "please call the office" reply so the member sees a clear next step."""
    mock_generate.side_effect = ClaudeUnavailable("no key")
    user = UserFactory(role="member")
    client.force_login(user)
    response = client.post("/assistant/chat/", {"message": "hi"})
    assert response.status_code == 200
    assert b"(555) 444-MEAL" in response.content


@pytest.mark.django_db
@patch("apps.ai_assistant.services.chat.generate")
def test_chat_truncates_long_messages(mock_generate, client):
    """Wall-of-text inputs must not eat the daily token budget."""
    mock_generate.return_value = "ok"
    user = UserFactory(role="member")
    client.force_login(user)
    response = client.post(
        "/assistant/chat/", {"message": "x" * 5000}
    )
    assert response.status_code == 200
    # The mocked client was called with at most 600 chars (the
    # _MAX_MESSAGE_LEN constant), so the cap actually triggered.
    sent_message = mock_generate.call_args.args[1]
    assert len(sent_message) == 600
