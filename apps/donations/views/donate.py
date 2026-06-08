"""Public donate views — anonymous, CSRF on.

* ``donate_page`` — GET, renders the form. Accepts ``?campaign=<slug>`` to
  deep-link a specific fundraiser, and ``?cancelled=1`` to show the soft
  toast after a Stripe Checkout abandonment (Story 5.4 wires the return URL).
* ``donate_start`` — POST, validates the form, calls the service, redirects
  to Stripe. Re-renders the form on validation errors so the user keeps
  their inputs.

The views are intentionally thin: they translate request data into a
``DonateForm`` and a ``start_donation`` call. All side effects live in the
service (per MerryMeal conventions).
"""

from __future__ import annotations

from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET, require_POST

from apps.donations.forms.donate import DonateForm
from apps.donations.models import Campaign
from apps.donations.services.campaigns import raised_cents_for
from apps.donations.services.donate import GENERAL_FUND_SLUG, start_donation


def _resolve_display_campaign(slug: str | None) -> Campaign | None:
    """Pick the campaign to display in the hero.

    Unknown / inactive slugs collapse to the general fund so a stale share
    link still renders a sensible page. Returns ``None`` only if the general
    fund seed is missing — which surfaces a 500 (deliberate: missing seed
    is a deploy bug we want to see, not paper over).
    """
    if slug and slug != GENERAL_FUND_SLUG:
        campaign = Campaign.objects.filter(slug=slug, is_active=True).first()
        if campaign is not None:
            return campaign
    return Campaign.objects.filter(slug=GENERAL_FUND_SLUG).first()


def _render_donate(request, form: DonateForm, campaign: Campaign | None):
    """Shared render helper for both GET and the invalid-POST re-render."""
    raised = raised_cents_for(campaign) if campaign else 0
    return render(
        request,
        "donations/donate.html",
        {
            "form": form,
            "campaign": campaign,
            "raised_cents": raised,
            "cancelled": request.GET.get("cancelled") == "1",
            # The chips are rendered in the template; keeping them as a
            # context list (instead of hard-coding the loop variable in the
            # template) makes them easy to A/B test later.
            "amount_chips": [20, 50, 100],
        },
    )


@require_GET
def donate_page(request):
    slug = request.GET.get("campaign") or ""
    campaign = _resolve_display_campaign(slug)
    # ``campaign_slug`` initial value is empty when we fell back to the
    # general fund — the form treats empty as "no specific campaign" and
    # ``start_donation`` resolves it again on POST. Pre-filling the exact
    # slug here would lock the gift to a stale share link even after the
    # campaign expires.
    initial_slug = slug if slug and slug != GENERAL_FUND_SLUG else ""
    form = DonateForm(initial={"campaign_slug": initial_slug})
    return _render_donate(request, form, campaign)


@require_POST
def donate_start(request):
    form = DonateForm(request.POST)
    if not form.is_valid():
        # Re-render with the user's inputs preserved. Fall back to the
        # general fund hero — if they typed a bad amount we don't want to
        # also lose them with a missing campaign reference.
        campaign = _resolve_display_campaign(
            request.POST.get("campaign_slug") or ""
        )
        return _render_donate(request, form, campaign)
    _donation, url = start_donation(
        campaign_slug=form.cleaned_data.get("campaign_slug") or None,
        amount_cents=form.cleaned_data["amount_cents"],
        donor_email=form.cleaned_data["donor_email"],
        is_recurring=form.cleaned_data["is_recurring"],
    )
    return redirect(url)
