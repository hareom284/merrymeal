"""Confirms the floating assistant widget actually renders on the
pages that extend ``app_base.html`` for each role."""
import pytest

from apps.accounts.tests.factories import UserFactory


@pytest.mark.django_db
def test_admin_home_renders_assistant_widget(client):
    """Admin role must see the floating bubble on /admin/home/ — the
    earlier 12.1 nav refactor hides the member bell for admins, so a
    regression that drops the widget here is easy to miss visually."""
    admin = UserFactory(role="admin")
    client.force_login(admin)
    response = client.get("/admin/home/")
    assert response.status_code == 200
    body = response.content
    assert b"assistant-chat-log" in body
    assert b"/admin/assistant/chat/" in body
    # Must NOT carry the member endpoint on an admin page.
    assert b'action="/assistant/chat/"' not in body


@pytest.mark.django_db
def test_member_dashboard_renders_member_widget(client):
    member = UserFactory(role="member")
    client.force_login(member)
    response = client.get("/dashboard/")
    assert response.status_code == 200
    body = response.content
    assert b"assistant-chat-log" in body
    assert b'action="/assistant/chat/"' in body
    # Must NOT carry the admin endpoint on a member page.
    assert b"/admin/assistant/chat/" not in body


@pytest.mark.django_db
def test_form_carries_native_post_action_for_no_js_fallback(client):
    """Even with HTMX, the form must keep ``method="post"`` + ``action=``
    so an HTMX failure to load (ad blocker, CDN block) still POSTs
    instead of falling through to a GET on the current URL."""
    admin = UserFactory(role="admin")
    client.force_login(admin)
    response = client.get("/admin/home/")
    body = response.content
    assert b'method="post"' in body
    assert b'action="/admin/assistant/chat/"' in body
