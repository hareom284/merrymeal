"""Mapbox Static Images URL builder (Story 12.7).

Pure URL composition — no HTTP call, no caching. The browser fetches
the image directly from Mapbox when the template renders an ``<img
src="...">`` against the returned URL, so a slow Mapbox response can
never block the page render.

If ``MAPBOX_TOKEN`` is unset (dev or test environments), :func:`static_map_url`
returns ``None`` and the template renders a stylised placeholder
instead. This is deliberate: we don't want builds to fail because a
local dev forgot to add the token to their ``.env``.
"""
from __future__ import annotations

from urllib.parse import quote

from django.conf import settings

_STYLE = "mapbox/streets-v12"
_DEFAULT_ZOOM = 14
_DEFAULT_SIZE = "640x320"


def static_map_url(
    lat: float | None,
    lon: float | None,
    *,
    zoom: int = _DEFAULT_ZOOM,
    size: str = _DEFAULT_SIZE,
) -> str | None:
    """Return a Mapbox Static Images API URL centered on (lat, lon).

    Returns ``None`` when no token is configured or coordinates are
    missing — the template falls back to a placeholder block in both
    cases.

    The pin colour is the brand green; ``@2x`` requests a retina image
    so the map stays sharp on mobile devices without doubling the
    rendered pixel size.
    """
    token = getattr(settings, "MAPBOX_TOKEN", "") or ""
    if not token or lat is None or lon is None:
        return None

    pin = f"pin-l+16a34a({lon},{lat})"
    centre = f"{lon},{lat},{zoom},0"
    path = f"/styles/v1/{_STYLE}/static/{pin}/{centre}/{size}@2x"
    return f"https://api.mapbox.com{path}?access_token={quote(token)}"
