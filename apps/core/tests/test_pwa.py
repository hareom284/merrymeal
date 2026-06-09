"""Tests for the PWA endpoints (manifest + service worker)."""
import json

import pytest


@pytest.mark.django_db
def test_service_worker_served_from_root(client):
    """The SW MUST live at /sw.js — a SW served from /static/sw.js can
    only control /static/* URLs, which makes the whole offline strategy
    pointless."""
    response = client.get("/sw.js")
    assert response.status_code == 200
    assert response["Content-Type"].startswith("application/javascript")
    body = b"".join(response.streaming_content) if response.streaming else response.content
    assert b"serviceWorker" in body or b"self.addEventListener" in body


@pytest.mark.django_db
def test_service_worker_carries_no_store_cache_headers(client):
    """A stale SW outliving a deploy is the single most painful PWA
    bug. ``no-store`` + ``must-revalidate`` guarantees the next page
    view fetches the fresh worker."""
    response = client.get("/sw.js")
    cache_control = response["Cache-Control"]
    assert "no-store" in cache_control
    assert "no-cache" in cache_control


@pytest.mark.django_db
def test_manifest_served_from_root(client):
    response = client.get("/manifest.webmanifest")
    assert response.status_code == 200
    assert response["Content-Type"].startswith("application/manifest+json")


@pytest.mark.django_db
def test_manifest_has_required_pwa_fields(client):
    """Chrome's PWA install criteria require name, icons, start_url,
    display. Asserting them here catches an edit that breaks
    installability before a real device does."""
    response = client.get("/manifest.webmanifest")
    body = b"".join(response.streaming_content) if response.streaming else response.content
    data = json.loads(body)
    assert data["name"] == "MerryMeal"
    assert data["display"] == "standalone"
    assert data["start_url"].startswith("/")
    assert any(icon["sizes"] == "192x192" for icon in data["icons"])
    assert any(icon["sizes"] == "512x512" for icon in data["icons"])


@pytest.mark.django_db
def test_landing_page_links_to_manifest_and_apple_icon(client):
    response = client.get("/")
    body = response.content
    assert b'rel="manifest"' in body
    assert b'href="/manifest.webmanifest"' in body
    assert b'rel="apple-touch-icon"' in body


@pytest.mark.django_db
def test_landing_registers_service_worker(client):
    response = client.get("/")
    body = response.content
    assert b"navigator.serviceWorker" in body
    assert b'register("/sw.js"' in body
