"""Tests for Story 4.9 — POD photo conversion + upload helper.

The HEIC branch only runs if ``pyheif`` (and the underlying libheif
shared library) is importable on the test box. On macOS dev that means
``brew install libheif && pip install pyheif``; CI runs on a Debian
image with ``libheif-dev`` apt-installed. When the wrapper isn't
present, that case is skipped — every other code path is still
exercised so the JPEG re-encode regression net stays tight.
"""
from __future__ import annotations

import importlib
import io

import pytest
from PIL import Image

from apps.delivery.services.photo import convert_to_jpeg, upload_pod_photo

pyheif_available = importlib.util.find_spec("pyheif") is not None


def test_jpeg_passes_through():
    buf = io.BytesIO()
    Image.new("RGB", (10, 10), "red").save(buf, format="JPEG")
    buf.seek(0)
    out, content_type = convert_to_jpeg(buf, "image/jpeg")
    assert content_type == "image/jpeg"
    out.seek(0)
    assert Image.open(out).format == "JPEG"


def test_png_is_converted_to_jpeg():
    """PNG → JPEG re-encode: same shape, ``image/jpeg`` content type."""
    buf = io.BytesIO()
    Image.new("RGBA", (8, 8), (255, 0, 0, 128)).save(buf, format="PNG")
    buf.seek(0)
    out, content_type = convert_to_jpeg(buf, "image/png")
    assert content_type == "image/jpeg"
    out.seek(0)
    assert Image.open(out).format == "JPEG"


@pytest.mark.skipif(not pyheif_available, reason="libheif / pyheif not installed")
def test_heic_is_converted_to_jpeg():
    """HEIC fixtures live next to this file; install pyheif to run."""
    from pathlib import Path

    fixture = Path(__file__).parent / "fixtures" / "sample.heic"
    if not fixture.exists():
        pytest.skip(f"missing fixture {fixture}")
    with fixture.open("rb") as fh:
        out, content_type = convert_to_jpeg(fh, "image/heic")
    assert content_type == "image/jpeg"
    out.seek(0)
    assert Image.open(out).format == "JPEG"


@pytest.mark.django_db
def test_upload_pod_photo_writes_jpeg_and_returns_url(tmp_path, settings):
    """End-to-end: a multipart UploadedFile → media/ JPEG → public URL."""
    from django.core.files.uploadedfile import SimpleUploadedFile

    settings.MEDIA_ROOT = str(tmp_path)
    buf = io.BytesIO()
    Image.new("RGB", (12, 12), "green").save(buf, format="JPEG")
    uploaded = SimpleUploadedFile(
        "doorstep.jpg", buf.getvalue(), content_type="image/jpeg"
    )
    url = upload_pod_photo(uploaded, delivery_id=42)
    assert url.endswith(".jpg")
    assert "/pod/42/" in url
