"""Tests for the admin notifications page + bell wiring (Story 12.9)."""
from datetime import timedelta

import pytest
from django.utils import timezone

from apps.accounts.models import Application
from apps.accounts.tests.factories import UserFactory
from apps.dashboards.services.admin_notifications import (
    admin_notification_count,
    build_admin_notifications,
)


@pytest.mark.django_db
def test_admin_notifications_requires_admin(client):
    user = UserFactory(role="member")
    client.force_login(user)
    response = client.get("/admin/notifications/")
    assert response.status_code == 403


@pytest.mark.django_db
def test_admin_notifications_renders_for_admin(client):
    admin = UserFactory(role="admin")
    client.force_login(admin)
    response = client.get("/admin/notifications/")
    assert response.status_code == 200
    assert b"Notifications" in response.content


@pytest.mark.django_db
def test_admin_notifications_returns_empty_list_when_nothing_pending():
    """No applications, no deliveries, no FS failures, no expiring
    stock → no notifications. The bell badge stays unlit."""
    assert build_admin_notifications() == []
    assert admin_notification_count() == 0


@pytest.mark.django_db
def test_admin_notifications_includes_pending_applications():
    Application.objects.create(
        full_name="Test Person",
        email="t@example.com",
        dob=(timezone.localdate() - timedelta(days=365 * 70)),
        status=Application.STATUS_SUBMITTED,
    )
    notifications = build_admin_notifications()
    assert len(notifications) == 1
    item = notifications[0]
    assert item["kind"] == "applications"
    assert item["count"] == 1
    assert "applications" in item["url"]


@pytest.mark.django_db
def test_admin_notifications_post_is_a_noop(client):
    """Mark all read is a 204 no-op — the list is synthesised, nothing
    to persist. CSRF off via force_login. POST must NOT raise."""
    admin = UserFactory(role="admin")
    client.force_login(admin)
    response = client.post("/admin/notifications/")
    assert response.status_code == 204


@pytest.mark.django_db
def test_admin_topbar_bell_points_at_admin_notifications(client):
    """Bell URL must come from the role-aware context processor, not
    a hardcoded ``{% url 'dashboards:notifications' %}`` that would
    404 for admins."""
    admin = UserFactory(role="admin")
    client.force_login(admin)
    response = client.get("/admin/home/")
    body = response.content
    assert b'href="/admin/notifications/"' in body
    # And NOT the member-only URL.
    assert b'href="/notifications/"' not in body


@pytest.mark.django_db
def test_member_topbar_bell_still_points_at_member_notifications(client):
    """Regression: generalising the bell mustn't break the member path."""
    member = UserFactory(role="member")
    client.force_login(member)
    response = client.get("/dashboard/")
    assert b'href="/notifications/"' in response.content


@pytest.mark.django_db
def test_volunteer_has_no_topbar_bell(client):
    """Roles without a notifications URL get no bell at all (an empty
    spacer keeps the topbar layout balanced)."""
    vol = UserFactory(role="volunteer")
    client.force_login(vol)
    # Volunteer redirects to delivery:volunteer_today, follow it.
    response = client.get("/dashboard/", follow=True)
    # The volunteer page may or may not use app_base; assert the bell
    # markup absent if app_base IS used.
    if b"aria-label=\"Notifications\"" in response.content:
        # It IS rendered — fail loudly so we know to gate this view too.
        pytest.fail("Volunteer page should not show a notifications bell yet")
