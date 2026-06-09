"""Tests for the synthesised notifications page (Story 12.6)."""
import datetime as dt

import pytest

from apps.accounts.tests.factories import UserFactory
from apps.dashboards.services.notifications import build_member_notifications
from apps.delivery.models import Delivery
from apps.delivery.tests.factories import DeliveryFactory


@pytest.mark.django_db
def test_notifications_page_requires_login(client):
    response = client.get("/notifications/")
    assert response.status_code == 302
    assert "/login/" in response.url or "/accounts/login/" in response.url


@pytest.mark.django_db
def test_notifications_page_renders_empty_state_when_no_activity(client):
    user = UserFactory(role="member")
    client.force_login(user)
    response = client.get("/notifications/")
    assert response.status_code == 200
    assert b"Nothing new right now" in response.content


@pytest.mark.django_db
def test_post_returns_204_for_mark_all_read(client):
    """The 'Mark all read' button is a no-op POST because the list is
    synthesised from live data; the view honours it to avoid a 405."""
    user = UserFactory(role="member")
    client.force_login(user)
    response = client.post("/notifications/")
    assert response.status_code == 204


@pytest.mark.django_db
def test_today_pending_delivery_surfaces_as_notification():
    member = UserFactory(role="member")
    today = dt.date.today()
    DeliveryFactory(member=member, scheduled_date=today, status=Delivery.STATUS_PENDING)
    items = build_member_notifications(member, today=today)
    delivery_items = [n for n in items if n["kind"] == "delivery"]
    assert len(delivery_items) == 1
    assert "scheduled" in delivery_items[0]["title"].lower() or "today" in delivery_items[0]["title"].lower()


@pytest.mark.django_db
def test_out_for_delivery_uses_volunteer_first_name():
    member = UserFactory(role="member")
    volunteer_user = UserFactory(role="volunteer", full_name="Sarah Kennedy")
    today = dt.date.today()
    DeliveryFactory(
        member=member,
        scheduled_date=today,
        status=Delivery.STATUS_OUT_FOR_DELIVERY,
        volunteer=volunteer_user,
    )
    items = build_member_notifications(member, today=today)
    delivery_items = [n for n in items if n["kind"] == "delivery"]
    assert "Sarah" in delivery_items[0]["body"]


@pytest.mark.django_db
def test_failed_delivery_surfaces_failure_reason():
    member = UserFactory(role="member")
    today = dt.date.today()
    DeliveryFactory(
        member=member,
        scheduled_date=today,
        status=Delivery.STATUS_FAILED,
        failure_reason="Nobody home",
    )
    items = build_member_notifications(member, today=today)
    delivery_items = [n for n in items if n["kind"] == "delivery"]
    assert delivery_items[0]["body"] == "Nobody home"


@pytest.mark.django_db
def test_yesterday_delivered_without_feedback_creates_feedback_item():
    member = UserFactory(role="member")
    today = dt.date.today()
    yesterday = today - dt.timedelta(days=1)
    delivery = DeliveryFactory(
        member=member,
        scheduled_date=yesterday,
        status=Delivery.STATUS_DELIVERED,
    )
    items = build_member_notifications(member, today=today)
    feedback_items = [n for n in items if n["kind"] == "feedback"]
    assert len(feedback_items) == 1
    assert delivery.meal_plan.meal.name in feedback_items[0]["title"]


@pytest.mark.django_db
def test_old_delivered_meal_is_not_surfaced():
    """Older than 2 days = no feedback prompt (matches dashboard service)."""
    member = UserFactory(role="member")
    today = dt.date.today()
    three_days_ago = today - dt.timedelta(days=3)
    DeliveryFactory(
        member=member,
        scheduled_date=three_days_ago,
        status=Delivery.STATUS_DELIVERED,
    )
    items = build_member_notifications(member, today=today)
    assert [n for n in items if n["kind"] == "feedback"] == []


@pytest.mark.django_db
def test_notifications_render_links_and_titles(client):
    member = UserFactory(role="member")
    client.force_login(member)
    today = dt.date.today()
    DeliveryFactory(member=member, scheduled_date=today, status=Delivery.STATUS_PENDING)
    response = client.get("/notifications/")
    assert response.status_code == 200
    body = response.content
    assert b"notification-delivery" in body
    assert b"Mark all read" in body
