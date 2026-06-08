import pytest
from django.urls import reverse

from apps.accounts.tests.factories import UserFactory


@pytest.mark.django_db
def test_member_dashboard_requires_login(client):
    response = client.get(reverse("dashboards:member"))
    assert response.status_code == 302
    assert reverse("accounts:login") in response.url


@pytest.mark.django_db
def test_member_dashboard_renders_for_authenticated_user(client):
    user = UserFactory(full_name="Margaret Chen", role="member")
    client.force_login(user)
    response = client.get(reverse("dashboards:member"))
    assert response.status_code == 200
    assert b"Hello, Margaret" in response.content
    assert b"Today's delivery" in response.content
    assert b"This week's menu" in response.content
    # Story 3.4 — the "today's meal" card is fed by ``get_today_card``.
    # A factory member with no address / no MealPlan resolves to the
    # empty-state copy; the previous hardcoded "Herb-roasted chicken"
    # mock is gone.
    assert b"No meal scheduled today" in response.content
    assert b"Rate yesterday's meal" in response.content


@pytest.mark.django_db
def test_sidebar_logout_form_present(client):
    user = UserFactory(role="member")
    client.force_login(user)
    response = client.get(reverse("dashboards:member"))
    assert reverse("accounts:logout").encode() in response.content
    assert b"Sign out" in response.content


@pytest.mark.django_db
def test_no_django_admin_routes_anywhere(client):
    """We don't ship Django's built-in admin. All operational UIs are
    custom views under /."""
    for path in ("/admin/", "/app/", "/app/manage/", "/app/admin/"):
        response = client.get(path)
        assert response.status_code == 404, f"{path} should 404, got {response.status_code}"


@pytest.mark.django_db
def test_root_redirects_authenticated_user_to_dashboard(client):
    user = UserFactory(role="member")
    client.force_login(user)
    response = client.get("/")
    assert response.status_code == 302
    assert response.url == "/dashboard/"


@pytest.mark.django_db
def test_member_dashboard_lives_at_slash_dashboard(client):
    user = UserFactory(role="member")
    client.force_login(user)
    response = client.get("/dashboard/")
    assert response.status_code == 200
    assert b"Today's delivery" in response.content


@pytest.mark.django_db
def test_sidebar_has_no_manage_data_link_even_for_admin(client):
    """No Django admin = no 'Manage data' link. Custom admin pages will
    add their own sidebar entries when built."""
    user = UserFactory(role="admin", is_staff=True)
    client.force_login(user)
    response = client.get(reverse("dashboards:member"))
    assert b"Manage data" not in response.content
    assert b"/app/manage/" not in response.content
