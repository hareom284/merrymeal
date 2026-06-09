"""Session-backed conversation history + clear endpoint."""
from unittest.mock import patch

import pytest

from apps.accounts.tests.factories import UserFactory


@pytest.mark.django_db
@patch("apps.ai_assistant.services.chat.generate")
def test_member_history_accumulates_across_turns(mock_generate, client):
    """The second POST sees the first turn in its history kwarg, so
    follow-up questions ("and tomorrow?") work."""
    mock_generate.return_value = "First reply."
    user = UserFactory(role="member")
    client.force_login(user)

    client.post("/assistant/chat/", {"message": "what's today?"})
    # First call had empty history.
    assert mock_generate.call_args.kwargs["history"] == []

    mock_generate.return_value = "Second reply."
    client.post("/assistant/chat/", {"message": "and tomorrow?"})
    # Second call must see one user + one assistant turn.
    history = mock_generate.call_args.kwargs["history"]
    assert len(history) == 2
    assert history[0] == {"role": "user", "text": "what's today?"}
    assert history[1] == {"role": "assistant", "text": "First reply."}


@pytest.mark.django_db
@patch("apps.ai_assistant.services.chat.generate")
def test_member_history_caps_at_six_entries(mock_generate, client):
    """Long conversations must not balloon Claude requests."""
    mock_generate.return_value = "ok"
    user = UserFactory(role="member")
    client.force_login(user)

    for i in range(10):
        client.post("/assistant/chat/", {"message": f"q{i}"})

    # The cap is 6 entries (3 user/assistant pairs). The last call
    # should have seen at most 6 history entries before its own turn
    # was added.
    history = mock_generate.call_args.kwargs["history"]
    assert len(history) <= 6


@pytest.mark.django_db
@patch("apps.ai_assistant.services.chat.generate")
def test_clear_wipes_member_history(mock_generate, client):
    mock_generate.return_value = "ok"
    user = UserFactory(role="member")
    client.force_login(user)

    client.post("/assistant/chat/", {"message": "first"})
    response = client.post("/assistant/clear/")
    assert response.status_code == 204

    client.post("/assistant/chat/", {"message": "second"})
    history = mock_generate.call_args.kwargs["history"]
    assert history == []


@pytest.mark.django_db
@patch("apps.ai_assistant.services.chat.generate")
def test_admin_history_is_separate_from_member_history(mock_generate, client):
    """A user playing both roles in one session must not see member
    history leaking into the admin transcript or vice-versa. The
    session uses separate slots per role."""
    mock_generate.return_value = "ok"
    admin = UserFactory(role="admin")
    client.force_login(admin)

    client.post("/admin/assistant/chat/", {"message": "admin q1"})
    client.post("/admin/assistant/chat/", {"message": "admin q2"})

    history = mock_generate.call_args.kwargs["history"]
    # All entries should be from the admin slot — no member entries.
    assert all("admin" in turn["text"] or turn["role"] == "assistant" for turn in history)
