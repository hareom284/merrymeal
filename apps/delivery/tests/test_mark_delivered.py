"""Tests for Story 4.9 — Mark-delivered with POD photo + offline queue.

Covers:
* ``apps.delivery.services.mark_delivered.mark_delivered`` — status,
  delivered_time, photo, geo, idempotency, auditlog.
* ``POST /volunteer/delivery/<pk>/mark-delivered/`` — auth scoping,
  404 for foreign deliveries, multipart photo upload, HTMX response,
  ``@require_POST`` enforcement.

Adaptations from the spec
-------------------------
* ``pytest-freezer`` is not installed; we monkeypatch the relevant
  ``timezone`` references rather than ``freezer.move_to``.
* The spec said audit-log was already registered; it isn't, so Story
  4.9 registers ``Delivery`` with ``auditlog.registry`` in
  ``apps/delivery/apps.py``. The tests just assert a LogEntry row
  appears — they don't care which sprint wired the signal.
* The view uses Django's ``default_storage`` (FileSystemStorage in dev
  / test). S3 uploads only kick in under ``config.settings.prod``.
"""
from __future__ import annotations

import datetime as dt
import io

import pytest
from auditlog.models import LogEntry
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.utils import timezone
from PIL import Image

from apps.accounts.tests.factories import UserFactory
from apps.delivery.tests.factories import DeliveryFactory, RouteFactory


def _jpeg_bytes(color: str = "red") -> bytes:
    """Tiny in-memory JPEG for upload fixtures."""
    buf = io.BytesIO()
    Image.new("RGB", (10, 10), color).save(buf, format="JPEG")
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Service-layer tests (Task 1 RED → Task 2 GREEN)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_mark_delivered_sets_status_and_time():
    from apps.delivery.services.mark_delivered import mark_delivered

    d = DeliveryFactory(status="pending")
    out = mark_delivered(
        d,
        photo_url="https://cdn.example/pod.jpg",
        lat=None,
        lng=None,
    )
    out.refresh_from_db()
    assert out.status == "delivered"
    assert out.delivered_time is not None
    assert out.photo == "https://cdn.example/pod.jpg"


@pytest.mark.django_db
def test_mark_delivered_tolerates_null_geo():
    from apps.delivery.services.mark_delivered import mark_delivered

    d = DeliveryFactory(status="pending")
    mark_delivered(d, photo_url="https://cdn/x.jpg", lat=None, lng=None)
    d.refresh_from_db()
    assert d.latitude is None
    assert d.longitude is None


@pytest.mark.django_db
def test_mark_delivered_persists_geo():
    from apps.delivery.services.mark_delivered import mark_delivered

    d = DeliveryFactory(status="pending")
    mark_delivered(d, photo_url="https://cdn/x.jpg", lat="-37.8136", lng="144.9631")
    d.refresh_from_db()
    assert str(d.latitude) == "-37.8136000"
    assert str(d.longitude) == "144.9631000"


@pytest.mark.django_db
def test_mark_delivered_writes_audit_log():
    from apps.delivery.services.mark_delivered import mark_delivered

    d = DeliveryFactory(status="pending")
    before = LogEntry.objects.filter(object_id=str(d.id)).count()
    mark_delivered(d, photo_url="https://x", lat="-37.81", lng="144.96")
    after = LogEntry.objects.filter(object_id=str(d.id)).count()
    assert after > before


@pytest.mark.django_db
def test_mark_delivered_idempotent_on_already_delivered():
    """Repeat calls on an already-delivered row must not overwrite anything.

    Short-circuit before ``save()`` so we don't spam the audit log with
    no-op updates (pitfall called out in the spec).
    """
    from apps.delivery.services.mark_delivered import mark_delivered

    original_time = timezone.now() - dt.timedelta(hours=1)
    d = DeliveryFactory(
        status="delivered",
        delivered_time=original_time,
        photo="https://cdn/first.jpg",
    )

    mark_delivered(d, photo_url="https://cdn/second.jpg", lat=None, lng=None)
    d.refresh_from_db()
    # delivered_time may have come back with a slightly different
    # microsecond resolution; assert by 1-second equality.
    assert abs((d.delivered_time - original_time).total_seconds()) < 1
    assert d.photo == "https://cdn/first.jpg"


# ---------------------------------------------------------------------------
# View-layer tests (Task 4)
# ---------------------------------------------------------------------------


@pytest.fixture
def upload_photo():
    """A 10x10 JPEG ``SimpleUploadedFile`` ready for a multipart POST."""
    return SimpleUploadedFile("pod.jpg", _jpeg_bytes(), content_type="image/jpeg")


@pytest.mark.django_db
def test_view_marks_delivery_delivered(client, upload_photo, tmp_path, settings):
    """Happy path: own delivery, photo uploads, status flips to delivered."""
    settings.MEDIA_ROOT = str(tmp_path)
    sarah = UserFactory(role="volunteer")
    route = RouteFactory(volunteer=sarah, route_date=dt.date.today())
    delivery = DeliveryFactory(
        volunteer=sarah,
        route=route,
        status="pending",
        scheduled_date=dt.date.today(),
    )
    client.force_login(sarah)

    resp = client.post(
        reverse("delivery:mark_delivered", args=[delivery.id]),
        data={"photo": upload_photo, "latitude": "-37.81", "longitude": "144.96"},
    )
    assert resp.status_code == 200
    delivery.refresh_from_db()
    assert delivery.status == "delivered"
    assert delivery.delivered_time is not None
    assert delivery.photo  # default_storage URL was written


@pytest.mark.django_db
def test_view_404_for_foreign_delivery(client, upload_photo, tmp_path, settings):
    """Volunteer A cannot mark Volunteer B's delivery — must be 404, not 403.

    404 (rather than 403) avoids leaking the existence of other
    volunteers' deliveries (spec acceptance criterion).
    """
    settings.MEDIA_ROOT = str(tmp_path)
    sarah = UserFactory(role="volunteer")
    other = UserFactory(role="volunteer", email="other@example.com")
    foreign = DeliveryFactory(volunteer=other, status="pending")
    client.force_login(sarah)

    resp = client.post(
        reverse("delivery:mark_delivered", args=[foreign.id]),
        data={"photo": upload_photo},
    )
    assert resp.status_code == 404
    foreign.refresh_from_db()
    assert foreign.status == "pending"


@pytest.mark.django_db
def test_view_404_for_missing_delivery(client, upload_photo):
    sarah = UserFactory(role="volunteer")
    client.force_login(sarah)
    resp = client.post(
        reverse("delivery:mark_delivered", args=[99999]),
        data={"photo": upload_photo},
    )
    assert resp.status_code == 404


@pytest.mark.django_db
def test_view_blocks_non_volunteer_role(client, upload_photo):
    member = UserFactory(role="member")
    client.force_login(member)
    # Need *some* delivery id; even if it existed, the role gate fires first.
    resp = client.post(
        reverse("delivery:mark_delivered", args=[1]),
        data={"photo": upload_photo},
    )
    assert resp.status_code == 403


@pytest.mark.django_db
def test_view_rejects_get(client):
    """``@require_POST`` — a GET must not flip status (spec pitfall)."""
    sarah = UserFactory(role="volunteer")
    delivery = DeliveryFactory(volunteer=sarah, status="pending")
    client.force_login(sarah)
    resp = client.get(reverse("delivery:mark_delivered", args=[delivery.id]))
    assert resp.status_code == 405
    delivery.refresh_from_db()
    assert delivery.status == "pending"


@pytest.mark.django_db
def test_view_400_when_photo_missing(client):
    sarah = UserFactory(role="volunteer")
    delivery = DeliveryFactory(volunteer=sarah, status="pending")
    client.force_login(sarah)
    resp = client.post(reverse("delivery:mark_delivered", args=[delivery.id]), data={})
    assert resp.status_code == 400
    delivery.refresh_from_db()
    assert delivery.status == "pending"


@pytest.mark.django_db
def test_view_returns_route_fragment(client, upload_photo, tmp_path, settings):
    """HTMX response is the rendered route fragment, not a full page."""
    settings.MEDIA_ROOT = str(tmp_path)
    sarah = UserFactory(role="volunteer")
    route = RouteFactory(volunteer=sarah, route_date=dt.date.today())
    d1 = DeliveryFactory(
        volunteer=sarah, route=route, status="pending",
        scheduled_date=dt.date.today(),
    )
    DeliveryFactory(
        volunteer=sarah, route=route, status="pending",
        scheduled_date=dt.date.today(),
    )
    client.force_login(sarah)

    resp = client.post(
        reverse("delivery:mark_delivered", args=[d1.id]),
        data={"photo": SimpleUploadedFile("p.jpg", _jpeg_bytes(),
                                          content_type="image/jpeg")},
    )
    assert resp.status_code == 200
    # The fragment includes the route container id; the full page wrapper
    # is in today.html and uses data-testid="today-screen".
    assert b"route-fragment" in resp.content
    assert b"today-screen" not in resp.content


@pytest.mark.django_db
def test_view_emits_structured_log(
    client, upload_photo, tmp_path, settings, caplog,
):
    """Spec: every success writes ``pod.delivered delivery=<id> volunteer=<id>``."""
    import logging

    settings.MEDIA_ROOT = str(tmp_path)
    sarah = UserFactory(role="volunteer")
    delivery = DeliveryFactory(volunteer=sarah, status="pending")
    client.force_login(sarah)

    with caplog.at_level(logging.INFO, logger="merrymeal.pod"):
        client.post(
            reverse("delivery:mark_delivered", args=[delivery.id]),
            data={"photo": upload_photo},
        )

    assert any(
        f"pod.delivered delivery={delivery.id} volunteer={sarah.id}" in r.getMessage()
        for r in caplog.records
    )
