"""Aggregation service backing the admin campaign-progress card (Story 5.8).

The campaign-progress view (``apps.dashboards.views.admin_campaigns``) needs
three numbers per campaign: raised cents, progress percentage and days
remaining until ``end_at``. Computing them inline in the view would scatter
the "money is integer cents" rule across templates, so the calculation lives
here behind a small ``CampaignProgress`` dataclass.

This module sits in the ``dashboards`` app — the top of the cross-app
dependency tree — so it may import ``Campaign`` and ``Donation`` from the
leaf ``donations`` app. The reverse import is forbidden by CLAUDE.md.

Only completed donations count toward ``raised_cents``; pending / refunded /
failed / cancelled rows are excluded. The same rule is enforced in
``apps.donations.services.campaigns.raised_cents_for`` (Story 5.1) — keep
them aligned if either rule changes.
"""

from __future__ import annotations

from dataclasses import dataclass

from django.db.models import Sum
from django.utils import timezone

from apps.donations.models import Campaign, Donation


@dataclass(frozen=True, slots=True)
class CampaignProgress:
    """Snapshot of a single campaign for the admin dashboard.

    ``pct`` is an integer 0–100 (capped) so the template can drop it into a
    Tailwind ``style="width: {{ pct }}%"`` without further coercion.
    ``days_remaining`` is ``None`` for open-ended campaigns (``end_at`` not
    set) and ``0`` for campaigns whose ``end_at`` has already passed — never
    negative.
    """

    campaign: Campaign
    raised_cents: int
    goal_cents: int
    pct: int
    days_remaining: int | None


def _raised(campaign: Campaign) -> int:
    """Sum completed donations for ``campaign``. Matches Story 5.1's helper."""
    return (
        Donation.objects.filter(campaign=campaign, status="completed").aggregate(
            t=Sum("amount_cents")
        )["t"]
        or 0
    )


def _days_remaining(campaign: Campaign) -> int | None:
    """Whole days from today (Melbourne) to ``end_at``; ``None`` if unset.

    Clamped to ``>= 0`` so a past ``end_at`` shows "0 days left" rather than
    a misleading negative count.
    """
    if campaign.end_at is None:
        return None
    today = timezone.localdate()
    end = timezone.localtime(campaign.end_at).date()
    return max(0, (end - today).days)


def progress_snapshot(campaign: Campaign) -> CampaignProgress:
    """Build a :class:`CampaignProgress` for one campaign."""
    raised = _raised(campaign)
    goal = int(campaign.goal_cents or 0)
    # Guard against a 0 / None goal: showing 100 % for a campaign with no
    # goal would be a worse lie than showing 0 %.
    pct = 0 if not goal else min(100, raised * 100 // goal)
    return CampaignProgress(
        campaign=campaign,
        raised_cents=raised,
        goal_cents=goal,
        pct=int(pct),
        days_remaining=_days_remaining(campaign),
    )


def list_active_campaigns() -> list[CampaignProgress]:
    """Snapshots for every ``is_active=True`` campaign, ordered by name."""
    return [
        progress_snapshot(c)
        for c in Campaign.objects.filter(is_active=True).order_by("name")
    ]
