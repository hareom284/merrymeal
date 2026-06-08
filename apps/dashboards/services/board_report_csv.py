"""Story 6.5 — CSV renderer for the board report.

A single CSV with a metric per row. The format is small enough that a
"sheet per metric" zip (the original sprint spec) would be overkill —
board members open this in Numbers/Excel, scroll once, and screenshot
the table into the meeting deck.

A UTF-8 BOM is prepended so Excel for Windows opens the file with the
correct encoding (without the BOM it falls back to cp1252 and breaks
on the "$" glyph in some locales).
"""
from __future__ import annotations

import csv
import io

from apps.dashboards.services.board_report import BoardReport

# Excel-on-Windows BOM marker; ``utf-8-sig`` prepends this automatically
# when *writing* but ``csv`` works on a ``StringIO`` so we add it once
# at the start of the returned string.
_BOM = "﻿"


def render_csv(report: BoardReport) -> str:
    """Return the CSV body (BOM-prefixed, ``\\r\\n`` line endings).

    Row order is fixed so spreadsheets diffed across months line up.
    Dollars are formatted as ``"$X.YY"`` for human reading; raw cents
    appear in a sibling column for spreadsheet maths.
    """
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["MerryMeal Board Report"])
    writer.writerow(["Period", report.period_label])
    writer.writerow([])  # blank separator row
    writer.writerow(["Metric", "Value", "Raw"])

    # Order matters — kept in sync with the PDF/HTML template so the
    # board sees the same sequence in every format.
    rows: list[tuple[str, str, str]] = [
        (
            "Donations total",
            _format_dollars(report.donations_total_cents),
            str(report.donations_total_cents),
        ),
        ("Donations count", str(report.donations_count), ""),
        ("Recurring donations count", str(report.recurring_count), ""),
        ("Deliveries completed", str(report.deliveries_completed), ""),
        ("Deliveries failed", str(report.deliveries_failed), ""),
        ("New members", str(report.new_members), ""),
        ("Active volunteers", str(report.active_volunteers), ""),
    ]
    for row in rows:
        writer.writerow(row)
    return _BOM + buf.getvalue()


def _format_dollars(amount_cents: int) -> str:
    """Render an integer cents value as ``"$1,234.56"``.

    ``amount_cents`` is always a non-negative integer in this codebase
    (donations are never refunded by a negative amount; refunds flip
    ``status`` instead). We still handle negatives defensively in case
    a future migration introduces them.
    """
    sign = "-" if amount_cents < 0 else ""
    cents = abs(amount_cents)
    dollars, remainder = divmod(cents, 100)
    return f"{sign}${dollars:,}.{remainder:02d}"
