"""Tests for the member-data snapshot the assistant grounds replies on."""
import pytest

from apps.accounts.tests.factories import UserFactory
from apps.ai_assistant.services.context import build_member_context


@pytest.mark.django_db
def test_context_includes_member_name():
    member = UserFactory(role="member", full_name="Margaret Wallace")
    snapshot = build_member_context(member)
    assert "Margaret Wallace" in snapshot


@pytest.mark.django_db
def test_context_announces_no_meal_when_none_scheduled():
    member = UserFactory(role="member")
    snapshot = build_member_context(member)
    assert "No meal scheduled" in snapshot


@pytest.mark.django_db
def test_context_falls_back_gracefully_when_composer_raises(monkeypatch):
    """A partner-affiliated member or other edge case could blow up the
    dashboard composer. The snapshot degrades to a name-only line
    instead of letting the chat 500."""
    import apps.ai_assistant.services.context as ctx_module

    def _boom(*a, **kw):
        raise RuntimeError("kaboom")

    monkeypatch.setattr(ctx_module, "build_member_dashboard_context", _boom)
    member = UserFactory(role="member", full_name="Margaret Wallace")
    snapshot = build_member_context(member)
    assert "Margaret Wallace" in snapshot
    assert "No live data available" in snapshot
