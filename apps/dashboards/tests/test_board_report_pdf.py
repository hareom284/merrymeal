"""Story 6.5 — PDF renderer.

Two branches to cover:

1. WeasyPrint and its native libs are installed (Docker image, some
   dev machines with ``brew install pango cairo``). ``render_pdf``
   returns ``bytes`` whose magic header is ``%PDF-``.
2. WeasyPrint cannot import (plain macOS / vanilla CI). ``render_pdf``
   returns ``None`` and the view layer falls back to HTML.

Both branches are exercised here so a regression in either is caught.
"""
from __future__ import annotations

import pytest

from apps.dashboards.services import board_report_pdf
from apps.dashboards.services.board_report import BoardReport


def _sample_report() -> BoardReport:
    return BoardReport(
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


def test_render_returns_none_when_weasyprint_unavailable(monkeypatch):
    """Simulate the local-dev path: WEASYPRINT_AVAILABLE is False, so
    the service degrades to ``None`` instead of raising."""
    monkeypatch.setattr(board_report_pdf, "WEASYPRINT_AVAILABLE", False)
    monkeypatch.setattr(board_report_pdf, "_weasyprint", None)
    assert board_report_pdf.render_pdf(_sample_report()) is None


def test_render_returns_pdf_bytes_when_weasyprint_available():
    """Only meaningful when the engine actually loads. ``importorskip``
    skips cleanly on dev machines without the native libs."""
    pytest.importorskip("weasyprint")
    # If the import succeeded but the module-level constant says
    # otherwise (e.g. native libs missing at load time), skip rather
    # than mis-report a failure for an environment issue.
    if not board_report_pdf.WEASYPRINT_AVAILABLE:
        pytest.skip("weasyprint imported but native libs unavailable")
    pdf = board_report_pdf.render_pdf(_sample_report())
    assert isinstance(pdf, bytes)
    assert pdf.startswith(b"%PDF-"), "missing PDF magic header"


def test_render_returns_none_when_engine_raises(monkeypatch):
    """A WeasyPrint runtime exception (e.g. font missing) must not
    bubble — the view falls back to HTML instead of 500."""

    class _BrokenHTML:
        def __init__(self, *a, **kw):
            pass

        def write_pdf(self):
            raise RuntimeError("simulated native-lib failure")

    class _StubModule:
        HTML = _BrokenHTML

    monkeypatch.setattr(board_report_pdf, "WEASYPRINT_AVAILABLE", True)
    monkeypatch.setattr(board_report_pdf, "_weasyprint", _StubModule)
    assert board_report_pdf.render_pdf(_sample_report()) is None
