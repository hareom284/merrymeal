import datetime as dt

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.accounts.tests.factories import UserFactory
from apps.delivery.tests.factories import DeliveryFactory


@pytest.mark.django_db
def test_member_dashboard_requires_login(client):
    response = client.get(reverse("dashboards:member"))
    assert response.status_code == 302
    assert reverse("accounts:login") in response.url


@pytest.mark.django_db
def test_member_dashboard_renders_for_authenticated_user(client):
    """Baseline empty-state render.

    A factory member with no MealPlan and no Delivery rows should still
    see the structural sections (hero, today's delivery header, week
    menu) and the honest empty-state copy for the meal card. The
    tracking pill and 2-tap feedback prompt require live ``Delivery``
    rows — they are covered by dedicated tests below.
    """
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


@pytest.mark.django_db
def test_member_dashboard_renders_live_tracking_pill_for_out_for_delivery(client):
    """Story 4.12 — when today's Delivery is out_for_delivery, the
    member dashboard must include the live tracking partial (the
    orphaned ``_member_today_card.html`` shell wraps it). Asserting on
    the stable ``data-testid`` markers from the partial proves the
    include path is wired."""
    member = UserFactory(full_name="Margaret Chen", role="member")
    volunteer = UserFactory(full_name="Sarah Khan", role="volunteer")
    DeliveryFactory(
        member=member,
        volunteer=volunteer,
        status="out_for_delivery",
        scheduled_date=timezone.localdate(),
    )
    client.force_login(member)
    response = client.get(reverse("dashboards:member"))
    assert response.status_code == 200
    assert b'data-testid="tracking-section"' in response.content
    assert b'data-testid="tracking-card"' in response.content
    # The volunteer-display helper trims to "Sarah K." (see
    # ``apps.delivery.services.tracking._volunteer_display``).
    assert b"Sarah K." in response.content


@pytest.mark.django_db
def test_member_dashboard_renders_feedback_cta_for_delivered_today(client):
    """Story 4.11 — when today's Delivery is ``delivered`` with NO
    DeliveryFeedback row, the dashboard must render the 2-tap feedback
    prompt (the same partial the standalone feedback URL renders)."""
    member = UserFactory(full_name="Margaret Chen", role="member")
    DeliveryFactory(
        member=member,
        status="delivered",
        scheduled_date=timezone.localdate(),
    )
    client.force_login(member)
    response = client.get(reverse("dashboards:member"))
    assert response.status_code == 200
    assert b'data-testid="feedback-section"' in response.content
    assert b'data-testid="feedback-card"' in response.content
    assert b"How was today's meal?" in response.content


@pytest.mark.django_db
def test_member_dashboard_renders_yesterday_feedback_prompt(client):
    """The "Rate yesterday's meal" CTA renders when there is a
    delivered Delivery in the last 2 days that the member has not yet
    rated. The composition service exposes this via ``feedback_prompt``;
    the template renders the section only when set, and embeds the
    canonical Story 4.11 feedback card inline."""
    member = UserFactory(full_name="Margaret Chen", role="member")
    yesterday = timezone.localdate() - dt.timedelta(days=1)
    DeliveryFactory(
        member=member,
        status="delivered",
        scheduled_date=yesterday,
    )
    client.force_login(member)
    response = client.get(reverse("dashboards:member"))
    assert response.status_code == 200
    assert b"Rate yesterday's meal</h3>" in response.content
    # The inline feedback card from Story 4.11 is embedded so the
    # member can rate without navigating away.
    assert b'data-testid="feedback-card"' in response.content


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
