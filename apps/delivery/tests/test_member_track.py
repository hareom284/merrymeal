"""Tests for the member track-delivery page (Story 12.7)."""
import datetime as dt

import pytest
from django.test import override_settings

from apps.accounts.tests.factories import UserFactory
from apps.delivery.models import Delivery
from apps.delivery.services.map_snapshot import static_map_url
from apps.delivery.tests.factories import DeliveryFactory

# ---- service ---------------------------------------------------------

def test_static_map_url_returns_none_without_token():
    """No token → no URL; the template falls back to a placeholder block."""
    with override_settings(MAPBOX_TOKEN=""):
        assert static_map_url(-37.81, 144.96) is None


def test_static_map_url_returns_none_when_coords_missing():
    """Even with a token, missing coords yield no URL — the template
    decides whether to render a placeholder or hide the section."""
    with override_settings(MAPBOX_TOKEN="pk.test"):
        assert static_map_url(None, 144.96) is None
        assert static_map_url(-37.81, None) is None
        assert static_map_url(None, None) is None


def test_static_map_url_includes_pin_and_token():
    with override_settings(MAPBOX_TOKEN="pk.test"):
        url = static_map_url(-37.81, 144.96)
    assert url is not None
    assert url.startswith("https://api.mapbox.com/styles/v1/")
    assert "pin-l+16a34a(144.96,-37.81)" in url
    assert "access_token=pk.test" in url
    assert "@2x" in url


# ---- view ------------------------------------------------------------

@pytest.mark.django_db
def test_track_page_requires_login(client):
    response = client.get("/track/")
    assert response.status_code == 302
    assert "/login/" in response.url or "/accounts/login/" in response.url


@pytest.mark.django_db
def test_track_page_shows_no_delivery_state_when_nothing_scheduled(client):
    member = UserFactory(role="member")
    client.force_login(member)
    response = client.get("/track/")
    assert response.status_code == 200
    assert b"No delivery scheduled" in response.content


@pytest.mark.django_db
def test_track_page_renders_today_delivery(client):
    member = UserFactory(role="member")
    client.force_login(member)
    DeliveryFactory(
        member=member,
        scheduled_date=dt.date.today(),
        status=Delivery.STATUS_OUT_FOR_DELIVERY,
    )
    response = client.get("/track/")
    assert response.status_code == 200
    body = response.content
    assert b"track-hero" in body
    assert b"On the way" in body


@pytest.mark.django_db
def test_track_page_falls_back_to_placeholder_without_token(client):
    """No token + no GPS → "Map preview unavailable" placeholder."""
    member = UserFactory(role="member")
    client.force_login(member)
    DeliveryFactory(
        member=member,
        scheduled_date=dt.date.today(),
        status=Delivery.STATUS_PENDING,
    )
    with override_settings(MAPBOX_TOKEN=""):
        response = client.get("/track/")
    assert response.status_code == 200
    assert b"Map preview unavailable" in response.content
    assert b"api.mapbox.com" not in response.content


@pytest.mark.django_db
def test_track_page_renders_map_image_when_token_set(client):
    """When a token is configured and the delivery has GPS, the
    template renders an actual <img> against the Mapbox URL."""
    from decimal import Decimal

    member = UserFactory(role="member")
    client.force_login(member)
    DeliveryFactory(
        member=member,
        scheduled_date=dt.date.today(),
        status=Delivery.STATUS_OUT_FOR_DELIVERY,
        latitude=Decimal("-37.81"),
        longitude=Decimal("144.96"),
    )
    with override_settings(MAPBOX_TOKEN="pk.test"):
        response = client.get("/track/")
    assert response.status_code == 200
    assert b"api.mapbox.com" in response.content
    assert b"Map preview unavailable" not in response.content
