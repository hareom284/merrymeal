"""Tests for the read-only audit log viewer (Story 6.6).

These tests cover:
- Access control (admin only).
- Filters (email, action, object_type, date range).
- Pagination at 50 entries per page.
- Read-only enforcement: no POST handler, no edit/delete routes.
- Diff panel renders the before/after JSON.
- Defence-in-depth: Django admin registers a read-only LogEntry admin.
- Performance: select_related keeps the per-page query count bounded.
"""
from datetime import UTC, datetime

import pytest
from auditlog.models import LogEntry
from django.contrib import admin
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django.urls.exceptions import NoReverseMatch

from apps.accounts.tests.factories import UserFactory


@pytest.fixture
def admin_user(db):
    return UserFactory(role="admin", email="admin@example.com")


@pytest.fixture
def margaret(db):
    return UserFactory(role="member", email="margaret@example.com")


def _log(actor, target, action=1, changes=None, ts=None):
    ct = ContentType.objects.get_for_model(target)
    return LogEntry.objects.create(
        actor=actor,
        content_type=ct,
        object_id=str(target.pk),
        object_repr=str(target),
        action=action,
        changes=changes or {},
        timestamp=ts or datetime.now(UTC),
    )


@pytest.mark.django_db
class TestAuditViewer:
    def test_admin_can_load(self, client, admin_user):
        client.force_login(admin_user)
        response = client.get(reverse("dashboards:audit_viewer"))
        assert response.status_code == 200

    def test_anonymous_redirected_to_login(self, client, db):
        response = client.get(reverse("dashboards:audit_viewer"))
        assert response.status_code == 302
        assert "/accounts/login" in response.url

    def test_non_admin_forbidden(self, client, db):
        u = UserFactory(role="member")
        client.force_login(u)
        response = client.get(reverse("dashboards:audit_viewer"))
        assert response.status_code in (302, 403)

    def test_filter_by_actor_email(self, client, admin_user, margaret):
        dietitian = UserFactory(
            role="kitchen_staff", email="diet@example.com"
        )
        _log(dietitian, margaret, changes={"diet": ["none", "gluten_free"]})
        _log(admin_user, margaret, changes={"is_active": [True, False]})

        client.force_login(admin_user)
        response = client.get(
            reverse("dashboards:audit_viewer") + "?email=diet"
        )
        rows = response.context["page_obj"].object_list
        assert len(rows) == 1
        assert all("diet" in r.actor.email for r in rows)

    def test_filter_by_action(self, client, admin_user, margaret):
        _log(admin_user, margaret, action=0)  # create
        _log(admin_user, margaret, action=2)  # delete
        client.force_login(admin_user)
        response = client.get(
            reverse("dashboards:audit_viewer") + "?action=delete"
        )
        rows = list(response.context["page_obj"].object_list)
        assert len(rows) == 1
        assert rows[0].action == 2

    def test_filter_by_object_type(self, client, admin_user, margaret):
        _log(admin_user, margaret, action=1)
        client.force_login(admin_user)
        response = client.get(
            reverse("dashboards:audit_viewer") + "?object_type=accounts.user"
        )
        rows = list(response.context["page_obj"].object_list)
        assert len(rows) >= 1
        for row in rows:
            assert row.content_type.app_label == "accounts"
            assert row.content_type.model == "user"

    def test_filter_unknown_object_type_returns_empty(
        self, client, admin_user, margaret
    ):
        # A typo like "accounts.User" (wrong case / non-existent) must
        # NOT 500 — the service catches ``DoesNotExist`` and returns
        # an empty queryset.
        _log(admin_user, margaret, action=1)
        client.force_login(admin_user)
        response = client.get(
            reverse("dashboards:audit_viewer") + "?object_type=nope.missing"
        )
        assert response.status_code == 200
        assert list(response.context["page_obj"].object_list) == []

    def test_pagination_50_per_page(self, client, admin_user, margaret):
        for _ in range(75):
            _log(admin_user, margaret, changes={"x": [1, 2]})
        client.force_login(admin_user)
        response = client.get(reverse("dashboards:audit_viewer"))
        page = response.context["page_obj"]
        assert page.paginator.per_page == 50
        assert len(page.object_list) == 50
        assert page.paginator.num_pages == 2

    def test_diff_panel_renders_changes(self, client, admin_user, margaret):
        _log(
            admin_user,
            margaret,
            changes={"diet": ["none", "gluten_free"]},
        )
        client.force_login(admin_user)
        response = client.get(reverse("dashboards:audit_viewer"))
        body = response.content.decode()
        # Field name + before + after values all appear in the diff panel.
        assert "diet" in body
        assert "none" in body
        assert "gluten_free" in body

    def test_no_post_handler(self, client, admin_user):
        client.force_login(admin_user)
        response = client.post(reverse("dashboards:audit_viewer"), {})
        # 405 method not allowed, NOT 200.
        assert response.status_code == 405

    def test_no_edit_or_delete_routes_exist(self):
        for name in ("audit_edit", "audit_delete"):
            with pytest.raises(NoReverseMatch):
                reverse(f"dashboards:{name}", args=[1])

    def test_query_count_stays_bounded(
        self, client, admin_user, margaret, django_assert_max_num_queries
    ):
        for _ in range(50):
            _log(admin_user, margaret, changes={"x": [1, 2]})
        client.force_login(admin_user)
        # Acceptance: ≤ 4 queries for the audit list itself. Auth /
        # session / pagination counting add a few more; allow 10 for
        # framework overhead while still catching N+1 regressions.
        with django_assert_max_num_queries(10):
            client.get(reverse("dashboards:audit_viewer"))


@pytest.mark.django_db
class TestAuditAdminDefence:
    def test_log_entry_admin_is_read_only(self):
        # Defence-in-depth: even the Django admin must not let staff
        # mutate audit rows. The dashboards app re-registers
        # ``LogEntry`` with all three permissions denied.
        admin_instance = admin.site._registry[LogEntry]
        assert admin_instance.has_add_permission(None) is False
        assert admin_instance.has_change_permission(None) is False
        assert admin_instance.has_delete_permission(None) is False
