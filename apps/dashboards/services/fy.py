"""Australian financial-year helpers.

Story 6.4.

The Australian financial year runs ``1 July`` to ``30 June``. The
*name* of the year is the calendar year it ends in: FY 2026 covers
``2025-07-01`` through ``2026-06-30``. Donors at tax time want a single
receipt for the FY just closed, hence this module: a tiny, dependency-
free pair of helpers used by both the view (route validation, period
boundaries) and the donor-history service
(:func:`apps.dashboards.services.donor_history.list_for_fy`).

Why ``date`` not ``datetime``
-----------------------------
Returning ``date`` objects (not timezone-aware datetimes) lets the
caller use ``created_at__date__gte`` / ``created_at__date__lte``. Django
evaluates ``__date`` lookups in the project ``TIME_ZONE``
(``Australia/Melbourne`` here), so a donation at
``2025-06-30 23:59:59`` Melbourne time correctly belongs to FY 2025 and
a donation one second later belongs to FY 2026 — even though both rows
are stored as UTC in the database. The boundary tests in
``test_fy_receipt.py`` pin this behaviour; do not switch to naive UTC
comparisons or you will silently shift every Melbourne-evening
donation into the wrong FY.
"""
from __future__ import annotations

from datetime import date

from django.utils import timezone


def fy_period(fy: int) -> tuple[date, date]:
    """Return ``(start, end)`` dates for the Australian FY ending in ``fy``.

    ``fy_period(2026) == (date(2025, 7, 1), date(2026, 6, 30))``. Both
    endpoints are inclusive — match with ``__date__gte`` / ``__date__lte``.
    """
    return date(fy - 1, 7, 1), date(fy, 6, 30)


def _current_fy() -> int:
    """The FY that includes ``today`` (Melbourne time).

    Months Jan–Jun are part of the FY ending this calendar year;
    months Jul–Dec are part of the FY ending next calendar year.
    """
    today = timezone.localdate()
    return today.year if today.month <= 6 else today.year + 1


def is_valid_fy(fy: int) -> bool:
    """Accept FYs from 2024 up to one year after the current FY.

    Lower bound: the MerryMeal donations table only exists from
    Sprint 09 (2024), so older FYs are guaranteed empty and asking for
    them is almost always a typo or a scraping bot. Upper bound: the
    *current* FY (allowed so donors can preview running totals before
    30 June) plus one. Out-of-range values raise 404 in the view,
    deliberately leaking nothing about the FY system to attackers.
    """
    return 2024 <= fy <= _current_fy() + 1
