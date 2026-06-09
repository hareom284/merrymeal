"""End-to-end tests for the /admin/assistant/chat/ endpoint."""
from unittest.mock import patch

import pytest

from apps.accounts.tests.factories import UserFactory
from apps.ai_assistant.services.client import ClaudeUnavailable


@pytest.mark.django_db
def test_admin_chat_requires_login(client):
    response = client.post("/admin/assistant/chat/", {"message": "hi"})
    assert response.status_code == 302


@pytest.mark.django_db
def test_admin_chat_rejects_member_role(client):
    user = UserFactory(role="member")
    client.force_login(user)
    response = client.post("/admin/assistant/chat/", {"message": "hi"})
    assert response.status_code in (302, 403)


@pytest.mark.django_db
@patch("apps.ai_assistant.services.chat.generate")
def test_admin_chat_returns_reply(mock_generate, client):
    mock_generate.return_value = "There are 3 failed deliveries today."
    admin = UserFactory(role="admin")
    client.force_login(admin)
    response = client.post(
        "/admin/assistant/chat/", {"message": "how many failed today?"}
    )
    assert response.status_code == 200
    body = response.content
    assert b"how many failed today?" in body
    assert b"3 failed deliveries" in body


@pytest.mark.django_db
@patch("apps.ai_assistant.services.chat.generate")
def test_admin_chat_uses_admin_system_prompt(mock_generate, client):
    """The admin endpoint must call ``generate`` with the OPERATIONAL
    system prompt, not the member one — otherwise asking about deliveries
    would get a "please call (555) 444-MEAL" reply."""
    mock_generate.return_value = "ok"
    admin = UserFactory(role="admin")
    client.force_login(admin)
    client.post("/admin/assistant/chat/", {"message": "status?"})
    system_prompt = mock_generate.call_args.args[0]
    assert "operations assistant" in system_prompt.lower()
    assert "Operational snapshot" in system_prompt


@pytest.mark.django_db
@patch("apps.ai_assistant.services.chat.generate")
def test_admin_chat_falls_back_when_claude_down(mock_generate, client):
    mock_generate.side_effect = ClaudeUnavailable("no key")
    admin = UserFactory(role="admin")
    client.force_login(admin)
    response = client.post(
        "/admin/assistant/chat/", {"message": "any failures?"}
    )
    assert response.status_code == 200
    assert b"/admin/home/" in response.content
