"""Partner outcomes view + CSV branch.

Story 6.2.

The view derives ``partner_id`` from ``request.user.partner_id`` —
never from the URL or query string. The :func:`partner_required`
decorator guarantees the column is non-NULL by the time the body runs.
"""
from __future__ import annotations

import csv
from io import StringIO

from django.http import HttpResponse
from django.shortcuts import render

from apps.core.decorators import partner_required
from apps.dashboards.services import partner_outcomes


@partner_required
def outcomes(request):
    partner_id = request.user.partner_id
    data = partner_outcomes.build(partner_id)

    if request.GET.get("format") == "csv":
        return _csv_response(data)
    return render(
        request,
        "dashboards/partner/outcomes.html",
        {**data, "page_title": "Partner outcomes"},
    )


def _csv_response(data: dict) -> HttpResponse:
    """Render the rows as an Excel-friendly CSV.

    The leading UTF-8 BOM (``﻿``) tells Excel to decode the file
    as UTF-8 so accented suburb / member names display correctly. Pure
    ``utf-8`` would render as mojibake on default Excel locales.
    """
    buf = StringIO()
    buf.write("﻿")  # BOM so Excel reads as UTF-8
    writer = csv.writer(buf)
    writer.writerow(
        [
            "Member",
            "Suburb",
            "Status",
            "Enrolment date",
            "Last delivery",
            "Average rating",
        ]
    )
    for r in data["rows"]:
        writer.writerow(
            [
                r["full_name"],
                r["suburb"],
                r["status"],
                r["enrolment_date"],
                r["last_delivery"] or "",
                f"{r['avg_rating']:.1f}"
                if r["avg_rating"] is not None
                else "",
            ]
        )
    resp = HttpResponse(
        buf.getvalue(), content_type="text/csv; charset=utf-8"
    )
    resp["Content-Disposition"] = (
        'attachment; filename="partner-outcomes.csv"'
    )
    return resp
