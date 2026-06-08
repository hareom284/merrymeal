"""Story 6.5 — Board report view.

GET ``/dashboard/admin/reports/board/?year=YYYY&month=MM&format=...``.

``format`` is one of:

* ``html`` (default) — printer-friendly page rendered inline. Includes
  a "Print to PDF" banner when the server-side PDF engine isn't
  available.
* ``csv`` — UTF-8 (with BOM) CSV download. ``Content-Disposition:
  attachment`` so browsers save it.
* ``pdf`` — PDF download when WeasyPrint loaded successfully at module
  import; otherwise the same HTML page with the fallback banner shown.

``year`` / ``month`` default to the *current* month in the project tz
(``Australia/Melbourne``). Passing a clearly out-of-range value
returns 400 — we explicitly do not silently coerce ``"2026-5"`` (no
zero-pad) into anything.
"""
from __future__ import annotations

from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import render
from django.utils import timezone

from apps.core.decorators import role_required
from apps.dashboards.services import board_report_pdf
from apps.dashboards.services.board_report import build_board_report
from apps.dashboards.services.board_report_csv import render_csv

_ALLOWED_FORMATS = {"html", "csv", "pdf"}


def _parse_int(raw: str | None, *, name: str) -> int | None:
    """Parse a query-string integer with a precise error message.

    Returns ``None`` when the param is absent so the caller can pick
    a default. Raises ``ValueError`` with the field name in the
    message on a bad value so the 400 response identifies which
    parameter the client got wrong.
    """
    if raw is None or raw == "":
        return None
    try:
        return int(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer") from exc


@role_required("admin")
def board_report_view(request):
    today = timezone.localdate()
    fmt = request.GET.get("format", "html").lower()
    if fmt not in _ALLOWED_FORMATS:
        return HttpResponseBadRequest(
            f"format must be one of {sorted(_ALLOWED_FORMATS)}"
        )

    try:
        # ``... is None`` rather than ``or default`` so an explicit
        # ``month=0`` still trips the validation branch below rather
        # than silently defaulting to today's month.
        year_raw = _parse_int(request.GET.get("year"), name="year")
        month_raw = _parse_int(request.GET.get("month"), name="month")
    except ValueError as exc:
        return HttpResponseBadRequest(str(exc))
    year = year_raw if year_raw is not None else today.year
    month = month_raw if month_raw is not None else today.month

    if not 1 <= month <= 12:
        return HttpResponseBadRequest("month must be 1..12")
    # Defensive cap — the queries technically work for any year, but
    # asking for the year 1 is almost certainly a typo and we'd rather
    # 400 than silently return zeros.
    if year < 2000 or year > 2100:
        return HttpResponseBadRequest("year must be 2000..2100")

    report = build_board_report(year=year, month=month)

    if fmt == "csv":
        csv_body = render_csv(report)
        # ``utf-8-sig`` would re-add the BOM; the renderer already
        # included it, so encode plain utf-8 here.
        resp = HttpResponse(csv_body.encode("utf-8"), content_type="text/csv; charset=utf-8")
        filename = f"board-report-{year:04d}-{month:02d}.csv"
        resp["Content-Disposition"] = f'attachment; filename="{filename}"'
        return resp

    if fmt == "pdf":
        pdf_bytes = board_report_pdf.render_pdf(report)
        if pdf_bytes is not None:
            resp = HttpResponse(pdf_bytes, content_type="application/pdf")
            filename = f"board-report-{year:04d}-{month:02d}.pdf"
            resp["Content-Disposition"] = f'attachment; filename="{filename}"'
            return resp
        # Fall through to HTML render with a banner. We don't redirect
        # because the admin already clicked "PDF" — a same-URL render
        # with a banner is friendlier than a URL flicker.
        return _render_html(request, report, pdf_fallback=True)

    return _render_html(request, report, pdf_fallback=False)


def _render_html(request, report, *, pdf_fallback: bool) -> HttpResponse:
    return render(
        request,
        "dashboards/admin/board_report.html",
        {
            "report": report,
            "pdf_fallback": pdf_fallback,
            "donations_total_dollars": _format_dollars(report.donations_total_cents),
            "for_pdf": False,
        },
    )


def _format_dollars(amount_cents: int) -> str:
    """Mirror of the CSV renderer's formatter — kept local to avoid a
    template tag round-trip just for this one number."""
    sign = "-" if amount_cents < 0 else ""
    cents = abs(amount_cents)
    dollars, remainder = divmod(cents, 100)
    return f"{sign}${dollars:,}.{remainder:02d}"
