"""Fixed-window rate limiter backed by Django's cache framework.

Two checks per request, in this order:

1. **Per-user** — caps a single member/admin's chat rate so one user
   can't drain the daily Gemini quota with a runaway script.
2. **Global** — caps the project's combined rate so the charity stays
   under the Gemini free tier's ``15 req/min`` ceiling with headroom.

A fixed window (``int(time.time() / window_seconds)``) is the
cheapest atomic counter that survives a multi-worker deployment: each
counter is a single ``cache.incr`` call that the cache backend
serialises for us. The window resets cleanly at the boundary — a user
who tripped the limit at the 59th second is unblocked at the 60th.

Sliding windows are more accurate but require a list-of-timestamps in
the cache; they're not worth the complexity for a chat widget that
talks to a single upstream LLM.
"""
from __future__ import annotations

import time
from dataclasses import dataclass

from django.conf import settings
from django.core.cache import cache


@dataclass(frozen=True)
class RateLimitResult:
    """``allowed=False`` means the caller should stop and tell the user
    to wait ``retry_after`` seconds. ``scope`` is the reason the limit
    fired (``"user"`` or ``"global"``) — useful for logs and tests."""

    allowed: bool
    retry_after: int = 0
    scope: str = ""


def _window_seconds() -> int:
    return int(getattr(settings, "GEMINI_RATE_LIMIT_WINDOW_SECONDS", 60))


def _per_user_cap() -> int:
    return int(getattr(settings, "GEMINI_RATE_LIMIT_PER_USER", 10))


def _global_cap() -> int:
    return int(getattr(settings, "GEMINI_RATE_LIMIT_GLOBAL", 12))


def _increment(key: str, window: int) -> int:
    """Atomically increment ``key`` and return the new value.

    ``cache.add`` only succeeds when the key doesn't exist, so we use
    it to seed the counter with a TTL; if the key was already there
    ``add`` returns False and we fall through to ``incr``. This pair
    is the canonical Django pattern for "init-or-increment with TTL".
    """
    if cache.add(key, 0, timeout=window):
        # Race-safe: another worker may have raced past this point
        # before our increment lands, so we still call ``incr`` below.
        pass
    try:
        return cache.incr(key)
    except ValueError:
        # Key was evicted between ``add`` and ``incr`` (rare — happens
        # only when the cache is under memory pressure). Re-seed and
        # treat this as the first hit in a fresh window.
        cache.set(key, 1, timeout=window)
        return 1


def check(user_id: int | str) -> RateLimitResult:
    """Returns whether ``user_id`` may send another message right now.

    Increments both the per-user and the global counter on every call,
    even if one of them trips — that keeps the bucket math honest. The
    *first* counter to exceed its cap decides the reason returned.
    """
    window = _window_seconds()
    bucket = int(time.time()) // window
    user_key = f"ai_rl:user:{user_id}:{bucket}"
    global_key = f"ai_rl:global:{bucket}"

    user_count = _increment(user_key, window)
    global_count = _increment(global_key, window)

    # ``retry_after`` is the seconds remaining in the current window —
    # the moment the window ticks over both counters reset.
    retry_after = window - (int(time.time()) % window)

    if user_count > _per_user_cap():
        return RateLimitResult(False, retry_after, "user")
    if global_count > _global_cap():
        return RateLimitResult(False, retry_after, "global")
    return RateLimitResult(True)
