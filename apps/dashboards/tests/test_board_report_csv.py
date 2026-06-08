"""Story 6.5 — CSV renderer (pure-string output, no DB)."""
from __future__ import annotations

import csv
import io

from apps.dashboards.services.board_report import BoardReport
from apps.dashboards.services.board_report_csv import render_csv


def _sample_report(**overrides) -> BoardReport:
    defaults = dict(
        period_label="June 2026",
        year=2026,
        month=6,
        donations_total_cents=123_456,
        donations_count=7,
        recurring_count=3,
        deliveries_completed=42,
        deliveries_failed=2,
        new_members=4,
        active_volunteers=9,
    )
    defaults.update(overrides)
    return BoardReport(**defaults)


class TestCsvShape:
    def test_starts_with_utf8_bom(self):
        body = render_csv(_sample_report())
        # ``﻿`` is the BOM codepoint. Encoded as UTF-8 it becomes
        # the three bytes EF BB BF.
        assert body.startswith("﻿")
        assert body.encode("utf-8").startswith(b"\xef\xbb\xbf")

    def test_includes_title_and_period_header(self):
        body = render_csv(_sample_report(period_label="January 2027"))
        assert "MerryMeal Board Report" in body
        assert "January 2027" in body


class TestCsvRows:
    """The row order is part of the public contract — the board
    compares this month's CSV side-by-side with last month's, so the
    sequence must not drift."""

    def _parse(self, body: str) -> list[list[str]]:
        # Strip BOM, then read with stdlib csv.
        body = body.lstrip("﻿")
        return list(csv.reader(io.StringIO(body)))

    def test_row_order_matches_spec(self):
        rows = self._parse(render_csv(_sample_report()))
        # Find the metric rows (after the blank separator + header).
        labels = [r[0] for r in rows if r and r[0] not in {
            "MerryMeal Board Report", "Period", "Metric", "",
        }]
        assert labels == [
            "Donations total",
            "Donations count",
            "Recurring donations count",
            "Deliveries completed",
            "Deliveries failed",
            "New members",
            "Active volunteers",
        ]

    def test_dollar_formatting_two_decimals(self):
        body = render_csv(_sample_report(donations_total_cents=123_456))
        # $1,234.56 — note the comma group separator and 2-decimal cents.
        assert "$1,234.56" in body
        # Raw cents column must still ship the integer for spreadsheet maths.
        assert ",123456" in body

    def test_zero_dollars_renders_clean(self):
        body = render_csv(_sample_report(donations_total_cents=0))
        assert "$0.00" in body

    def test_values_match_dataclass(self):
        report = _sample_report(
            donations_count=11,
            recurring_count=5,
            deliveries_completed=99,
            deliveries_failed=1,
            new_members=7,
            active_volunteers=14,
        )
        rows = self._parse(render_csv(report))
        as_dict = {r[0]: r[1] for r in rows if len(r) >= 2}
        assert as_dict["Donations count"] == "11"
        assert as_dict["Recurring donations count"] == "5"
        assert as_dict["Deliveries completed"] == "99"
        assert as_dict["Deliveries failed"] == "1"
        assert as_dict["New members"] == "7"
        assert as_dict["Active volunteers"] == "14"
