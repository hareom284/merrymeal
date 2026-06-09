"""Service: start a public donation.

Per MerryMeal conventions all side effects (DB writes, Stripe calls, email)
live in services — views stay thin. ``start_donation`` is the single entry
point for the public donate page: it writes the pending ``Donation`` row and
hands off to the Stripe Checkout helper (Story 5.4 ``stripe_checkout``).

Money is integer cents the whole way through; the form
(``DonateForm.clean_amount_dollars``) is the only place a user-typed dollar
string is parsed, and the service guards the type at its own boundary so a
mis-wired caller blows up loudly instead of silently storing 0.
"""

from __future__ import annotations

from apps.donations.models import Campaign, Donation
from apps.donations.services.stripe_checkout import create_checkout_session

# Sentinel slug for the catch-all "no campaign chosen" bucket. The general
# fund row itself is seeded by the Admin/Ops track in this sprint; the
# donate view does NOT create it on the fly because a missing seed is the
# kind of thing reviewers want to notice in CI, not paper over.
GENERAL_FUND_SLUG = "general-fund"


def _resolve_campaign(slug: str | None) -> Campaign:
    """Resolve ``slug`` to an active ``Campaign``, falling back to general fund.

    Unknown / inactive slugs collapse to the general fund instead of 500ing
    the form — a stale share link should still take the gift.
    """
    if slug:
        try:
            return Campaign.objects.get(slug=slug, is_active=True)
        except Campaign.DoesNotExist:
            pass
    return Campaign.objects.get(slug=GENERAL_FUND_SLUG)


def start_donation(
    *,
    campaign_slug: str | None,
    amount_cents: int,
    donor_email: str,
    is_recurring: bool,
) -> tuple[Donation, str]:
    """Create a pending Donation and return ``(donation, checkout_url)``.

    The donation lands in ``status='pending'``; Story 5.4's Stripe webhook
    flips it to ``completed`` once the card actually charges. Returning the
    URL (rather than redirecting here) keeps the service free of Django
    HTTP types — the view does the ``redirect()``.
    """
    if not isinstance(amount_cents, int) or isinstance(amount_cents, bool):
        # bool is a subclass of int — reject it explicitly so a stray
        # ``True`` doesn't store 1c by accident. The form parser is the
        # only legitimate source of ``amount_cents`` and it always returns
        # a plain int.
        raise TypeError("amount_cents must be int (integer cents)")
    campaign = _resolve_campaign(campaign_slug)
    donation = Donation.objects.create(
        campaign=campaign,
        donor_email=donor_email,
        amount_cents=amount_cents,
        payment_type="card",
        status="pending",
        is_recurring=is_recurring,
    )
    url = create_checkout_session(donation.id, recurring=is_recurring)
    return donation, url
