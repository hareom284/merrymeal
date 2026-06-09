"""Tests for the standalone rate-meal page (Story 12.8)."""

import pytest

from apps.accounts.tests.factories import UserFactory
from apps.delivery.models import Delivery
from apps.delivery.tests.factories import DeliveryFactory, DeliveryFeedbackFactory


@pytest.mark.django_db
def test_rate_page_requires_login(client):
    response = client.get("/rate/1/")
    assert response.status_code == 302
    assert "/login/" in response.url or "/accounts/login/" in response.url


@pytest.mark.django_db
def test_rate_page_404s_for_non_owner():
    """A logged-in member who doesn't own this delivery gets 404 — same
    convention as the feedback POST endpoint to keep delivery IDs
    unenumerable."""
    from django.test import Client

    owner = UserFactory(role="member")
    other = UserFactory(role="member", email="other@example.com")
    delivery = DeliveryFactory(member=owner, status=Delivery.STATUS_DELIVERED)

    c = Client()
    c.force_login(other)
    response = c.get(f"/rate/{delivery.id}/")
    assert response.status_code == 404


@pytest.mark.django_db
def test_rate_page_404s_for_pending_delivery(client):
    """A pending stop has nothing to rate."""
    member = UserFactory(role="member")
    client.force_login(member)
    delivery = DeliveryFactory(member=member, status=Delivery.STATUS_PENDING)
    response = client.get(f"/rate/{delivery.id}/")
    assert response.status_code == 404


@pytest.mark.django_db
def test_rate_page_renders_meal_info(client):
    member = UserFactory(role="member")
    client.force_login(member)
    delivery = DeliveryFactory(member=member, status=Delivery.STATUS_DELIVERED)
    response = client.get(f"/rate/{delivery.id}/")
    assert response.status_code == 200
    body = response.content
    assert delivery.meal_plan.meal.name.encode() in body
    assert b"Rate your meal" in body
    # Embeds the existing feedback partial.
    assert b"feedback-card" in body
    assert b"Skip for now" in body


@pytest.mark.django_db
def test_rate_page_shows_already_rated_state(client):
    member = UserFactory(role="member")
    client.force_login(member)
    delivery = DeliveryFactory(member=member, status=Delivery.STATUS_DELIVERED)
    DeliveryFeedbackFactory(delivery=delivery, rating=4)
    response = client.get(f"/rate/{delivery.id}/")
    assert response.status_code == 200
    assert b"already have your rating" in response.content
    # The form must NOT re-render once rated.
    assert b"feedback-card" not in response.content
