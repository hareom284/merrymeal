"""POD photo helpers: HEIC → JPEG conversion + storage upload (Story 4.9).

The service layer hides the difference between dev (local
``FileSystemStorage`` under ``media/``) and prod (``django-storages``
S3 backend). Callers just hand us the uploaded file and a delivery id;
we hand back a public URL ready to drop into ``Delivery.photo``.

Why we re-encode every photo as JPEG
------------------------------------
* iOS Safari uploads HEIC by default; browsers can't render it and S3
  treats it as binary. We convert.
* For PNG / WebP / JPEG inputs we still re-encode at quality 85 so the
  bucket only ever holds one mime-type (simplifies CDN cache rules and
  cuts size on the average 4MB iPhone capture by ~70%).
"""
from __future__ import annotations

import io
import logging

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from PIL import Image

try:  # pragma: no cover - import guard, exercised by skip in tests
    import pyheif
except ImportError:
    pyheif = None

logger = logging.getLogger("merrymeal.pod")


HEIC_TYPES = {"image/heic", "image/heif"}


def convert_to_jpeg(fh, content_type: str):
    """Return ``(BytesIO, 'image/jpeg')``.

    * HEIC / HEIF → decoded via ``pyheif``, re-encoded as JPEG.
    * Everything else → opened with Pillow, flattened to RGB, encoded
      as JPEG (quality=85, optimize=True).
    """
    if content_type in HEIC_TYPES:
        if pyheif is None:
            raise RuntimeError(
                "libheif / pyheif missing — install libheif (brew on macOS,"
                " apt-get install libheif-dev on Debian) and pip install pyheif."
            )
        heif = pyheif.read(fh.read())
        img = Image.frombytes(
            heif.mode, heif.size, heif.data, "raw", heif.mode, heif.stride
        )
    else:
        img = Image.open(fh).convert("RGB")

    out = io.BytesIO()
    img.save(out, format="JPEG", quality=85, optimize=True)
    out.seek(0)
    return out, "image/jpeg"


def upload_pod_photo(uploaded_file, *, delivery_id: int) -> str:
    """Convert + upload the POD photo, return the public URL.

    The storage backend (``default_storage``) is FileSystemStorage in
    dev / test and ``S3Boto3Storage`` in prod (see config/settings/prod.py).
    """
    content_type = getattr(uploaded_file, "content_type", "") or "image/jpeg"
    buf, _ = convert_to_jpeg(uploaded_file, content_type)

    original = getattr(uploaded_file, "name", "pod.jpg")
    stem = original.rsplit(".", 1)[0] if "." in original else original
    name = f"pod/{delivery_id}/{stem}.jpg"

    path = default_storage.save(name, ContentFile(buf.read()))
    url = default_storage.url(path)
    logger.debug("pod.uploaded delivery=%s path=%s", delivery_id, path)
    return url
