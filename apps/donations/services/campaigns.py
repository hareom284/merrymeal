"""Read-side helpers for campaigns.

The single source of truth for "how much has this campaign raised" lives
here so the admin progress bar, the public donate page (Story 5.3) and the
weekly fundraising digest (Story 5.8) all hit the same query.

Only completed donations count toward ``raised_cents``. Pending /
refunded / failed / cancelled rows are excluded — the progress bar
reflects money actually received, not money pledged.
"""

from __future__ import annotations

from django.db.models import Sum


def raised_cents_for(campaign) -> int:
    """Sum of ``amount_cents`` for completed donations on ``campaign``.

    Returns 0 if the ``Donation`` model has not landed yet (Story 5.2 fills
    it in). The lazy import keeps Story 5.1 self-sufficient — the admin
    progress bar renders at 0 % until donations exist.
    """
    try:
        from apps.donations.models import Donation
    except ImportError:
        return 0

    aggregate = (
        Donation.objects
        .filter(campaign_id=campaign.id, status="completed")
        .aggregate(total=Sum("amount_cents"))
    )
    return aggregate.get("total") or 0
