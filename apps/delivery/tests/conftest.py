"""Shared pytest fixtures for apps/delivery/tests/.

The `freezer` fixture mirrors the pattern from
`apps/planning/tests/test_validate_command.py` — a tiny stand-in for
freezegun / pytest-freezer that monkeypatches the bits of the codebase
that read "today" (`django.utils.timezone.localdate`).
"""
import datetime as dt

import pytest


@pytest.fixture
def freezer(monkeypatch):
    """Lightweight date-pinning fixture.

    Mimics the small slice of the freezegun / pytest-freezer API we use:
    `freezer.move_to("YYYY-MM-DD")` rewrites `timezone.localdate()` so
    code that consults the local Melbourne date sees the pinned value.
    Tests in `apps/delivery/tests/` pass dates directly to the dispatch
    service, but call `move_to` for consistency with the planning
    fixture and to keep `run_for_today()` deterministic.
    """

    class _Freezer:
        def move_to(self, iso: str) -> None:
            target = dt.date.fromisoformat(iso)
            import django.utils.timezone as tz

            monkeypatch.setattr(tz, "localdate", lambda: target)

    return _Freezer()
