"""Admin campaign-progress views (Story 5.8).

Three GET-only views, all gated by ``@role_required("admin")``:

* ``index`` — list of active campaigns with progress bars.
* ``detail`` — one campaign, paginated donations table, status filter.
* ``export_csv`` — streaming CSV of every donation on a campaign.

Routed at ``/admin/campaigns/...`` (config/urls.py). Distinct from Django's
built-in admin (which is not mounted in MerryMeal — all admin UI lives under
``apps.dashboards``).
"""

import csv

from django.core.paginator import Paginator
from django.http import StreamingHttpResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_GET

from apps.core.decorators import role_required
from apps.dashboards.services.campaign_csv import iter_csv_rows
from apps.dashboards.services.campaign_progress import (
    list_active_campaigns,
    progress_snapshot,
)
from apps.donations.models import Campaign, Donation

# Statuses surfaced as filter chips on the detail page. Mirrors
# ``Donation.STATUS_CHOICES`` minus ``failed`` (admins rarely look at failed
# rows; they show up in Stripe instead).
DETAIL_FILTER_STATUSES = ("completed", "pending", "refunded", "cancelled")

# Streaming CSV needs a file-like object with a ``write`` method. The
# ``StreamingHttpResponse`` consumes whatever ``csv.writer.writerow`` returns
# from ``Echo.write`` — the trick is that ``writerow`` actually returns the
# encoded line, so we just hand it back unchanged.
class _Echo:
    """File-like that returns the bytes it is asked to write."""

    def write(self, value):  # noqa: D401 — Django convention
        return value


@require_GET
@role_required("admin")
def index(request):
    return render(
        request,
        "dashboards/admin/campaigns.html",
        {
            "campaigns": list_active_campaigns(),
            "page_title": "Campaigns",
        },
    )


@require_GET
@role_required("admin")
def detail(request, slug: str):
    campaign = get_object_or_404(Campaign, slug=slug)
    snap = progress_snapshot(campaign)

    qs = Donation.objects.filter(campaign=campaign).order_by("-created_at")
    status_filter = request.GET.get("status") or ""
    if status_filter in DETAIL_FILTER_STATUSES:
        qs = qs.filter(status=status_filter)
    else:
        # Anything outside the allowed set is silently ignored — same
        # behaviour as the application-list filter (Sprint 04).
        status_filter = ""

    paginator = Paginator(qs, 25)
    page = paginator.get_page(request.GET.get("page"))
    return render(
        request,
        "dashboards/admin/campaign_detail.html",
        {
            "snap": snap,
            "page": page,
            "status_filter": status_filter,
            "filter_statuses": DETAIL_FILTER_STATUSES,
            "page_title": snap.campaign.name if hasattr(snap, "campaign") else "Campaign",
        },
    )


@require_GET
@role_required("admin")
def export_csv(request, slug: str):
    campaign = get_object_or_404(Campaign, slug=slug)
    # Ordered ascending so a reproducible CSV download is byte-stable
    # between requests (handy for diffing exports week-over-week).
    qs = Donation.objects.filter(campaign=campaign).order_by("created_at")

    writer = csv.writer(_Echo())
    response = StreamingHttpResponse(
        (writer.writerow(row) for row in iter_csv_rows(qs)),
        content_type="text/csv",
    )
    response["Content-Disposition"] = (
        f'attachment; filename="{slug}-donations.csv"'
    )
    return response
