"""Donor history view (``/donor/history/``) and FY receipt view
(``/donor/receipts/<fy>/``).

Story 6.3 — list every donation for the logged-in donor, newest first.
Story 6.4 — printer-friendly FY tax receipt for the same donor.
Both views are thin by design: gate on role, call the service, render.

Role gate
---------
``@role_required('donor')`` redirects anonymous users to the login
page and returns 403 for any non-donor authenticated user (members,
volunteers, caregivers, kitchen staff, admins). The ``donor`` role
exists in the ``users.role`` enum (see Sprint 02), so we do not need
the partner-fallback pattern Story 6.2 used for partner staff.
"""
from __future__ import annotations

from django.conf import settings
from django.http import Http404, JsonResponse
from django.shortcuts import render
from django.utils import timezone

from apps.core.decorators import role_required
from apps.dashboards.services import fy as fy_service
from apps.dashboards.services.donor_history import donor_history, list_for_fy


@role_required("donor")
def donor_history_view(request):
    donations = donor_history(request.user)
    # Annotate each row with its FY ending year so the template can
    # link directly at the existing ``dashboards:donor_fy_receipt`` page
    # (Story 6.4). Computed in the view rather than the service so the
    # service stays a pure list-of-Donation query.
    for donation in donations:
        donation.fy = fy_service.fy_for_date(timezone.localtime(donation.created_at).date())
    return render(
        request,
        "dashboards/donor/history.html",
        {
            "donations": donations,
            "active": "history",
            "page_title": "My donations",
        },
    )


@role_required("donor")
def fy_receipt(request, fy: int):
    """Render the FY tax receipt — HTML by default, JSON on
    ``?format=json``.

    Story 6.4. The page is the donor's single sheet for the tax
    return: total donated in the FY, an itemised table, and the
    charity ABN + address footer. Print stylesheet hides site chrome
    so a browser's "Print → Save as PDF" produces a clean A4.

    Out-of-range FY (``< 2024`` or ``> current_fy + 1``) raises 404 so
    the page never advertises its bounds. The same 404 fires for any
    non-integer path segment via the ``<int:fy>`` URL converter.
    """
    if not fy_service.is_valid_fy(fy):
        raise Http404("Unknown financial year.")

    start, end = fy_service.fy_period(fy)
    rows, total = list_for_fy(request.user, fy)

    if request.GET.get("format") == "json":
        return JsonResponse(
            {
                "fy": fy,
                "period": {
                    "start": start.isoformat(),
                    "end": end.isoformat(),
                },
                "donor": {
                    "name": getattr(request.user, "full_name", "") or "",
                    "email": request.user.email,
                },
                "donations": [
                    {
                        "date": r["created_at"].date().isoformat(),
                        "amount_cents": r["amount_cents"],
                        "campaign": r["campaign_name"],
                        "transaction_id": r["transaction_id"],
                        "receipt_number": r["receipt_number"],
                    }
                    for r in rows
                ],
                "total_cents": total,
                "charity": {
                    "abn": settings.MERRYMEAL_ABN,
                    "address": settings.MERRYMEAL_ADDRESS,
                },
            }
        )

    return render(
        request,
        "dashboards/donor/fy_receipt.html",
        {
            "fy": fy,
            "period_start": start,
            "period_end": end,
            "rows": rows,
            "total_cents": total,
            "abn": settings.MERRYMEAL_ABN,
            "address": settings.MERRYMEAL_ADDRESS,
        },
    )
