"""Expose the singleton ``OrgSettings`` row as ``org`` in every
template so ``{{ org.phone }}``, ``{{ org.logo_url }}`` etc. work
everywhere without each view having to pass them through.

The lookup is cached for 60 seconds via Django's cache framework so
this context processor adds essentially zero query overhead on busy
pages (the admin home, the audit viewer, kitchens) where strict
query-budget tests would otherwise regress.

Cache invalidation is handled by the ``post_save`` signal on
``OrgSettings`` — saving from the CRUD page drops the cached row so
the next page load picks up the change immediately.
"""
from __future__ import annotations

from django.core.cache import cache
from django.db.models.signals import post_save
from django.dispatch import receiver

_CACHE_KEY = "site_config:org"
_CACHE_TTL = 60  # seconds


def _load_from_db():
    from apps.site_config.models import OrgSettings
    return OrgSettings.objects.current()


def org(request):
    cached = cache.get(_CACHE_KEY)
    if cached is not None:
        return {"org": cached}
    try:
        obj = _load_from_db()
    except Exception:
        # During ``migrate`` or before the table exists yet — return
        # None so templates fall back gracefully rather than 500ing.
        return {"org": None}
    cache.set(_CACHE_KEY, obj, _CACHE_TTL)
    return {"org": obj}


@receiver(post_save, sender="site_config.OrgSettings")
def _invalidate_on_save(sender, **kwargs):
    """Drop the cached row when an admin saves the CRUD form so the
    next page load picks up the new phone / address / logo without
    waiting for the TTL."""
    cache.delete(_CACHE_KEY)
