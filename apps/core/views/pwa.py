"""PWA endpoints — serve the service worker and manifest from the site
root so the SW can claim a root scope (a SW served from ``/static/sw.js``
can only control ``/static/*`` URLs).

The bytes themselves still live under ``static/`` so the build pipeline
and ``collectstatic`` continue to treat them as static assets; the views
here just re-serve them at the canonical root paths.
"""
from __future__ import annotations

from django.conf import settings
from django.http import FileResponse, Http404
from django.views.decorators.cache import cache_control
from django.views.decorators.http import require_GET


def _serve_static(filename: str, content_type: str):
    """Locate ``filename`` in the project's ``static/`` dir and stream it."""
    for staticfiles_dir in settings.STATICFILES_DIRS:
        candidate = staticfiles_dir / filename
        if candidate.exists():
            return FileResponse(open(candidate, "rb"), content_type=content_type)
    raise Http404(filename)


@require_GET
@cache_control(max_age=0, no_cache=True, no_store=True, must_revalidate=True)
def service_worker(request):
    """Serve ``static/sw.js`` at ``/sw.js`` so it can register at the
    root scope and intercept fetches for the whole site. ``no-store``
    so a stale SW never sticks around longer than a single deploy."""
    return _serve_static("sw.js", "application/javascript")


@require_GET
@cache_control(max_age=3600, public=True)
def manifest(request):
    """Serve ``static/manifest.webmanifest`` at ``/manifest.webmanifest``.

    Strictly the manifest works from ``/static/manifest.webmanifest``
    too, but keeping it at the root lets us swap to a server-rendered
    one later (e.g. per-role start_url) without breaking installed
    clients that already point at this URL.
    """
    return _serve_static("manifest.webmanifest", "application/manifest+json")
