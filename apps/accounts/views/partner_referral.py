"""Story 6.7 — public partner referral form view.

The form lives at ``/partners/refer/`` and is intentionally
**unauthenticated** so a social worker at a referring charity can
submit a member on behalf of their client without needing a MerryMeal
account.

Anti-abuse: a honeypot field (``website``) silently absorbs trivial
bot submissions, and a per-IP rate-limit (5 successful POSTs per
hour) keeps a script-kiddie from flooding the queue.
"""

from __future__ import annotations

from django.core.cache import cache
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from apps.accounts.forms.partner_referral import PartnerReferralForm
from apps.accounts.services.applications import create_partner_referral

# 5 submissions per hour per IP. The story DoD picks this number as a
# balance: low enough to throttle scripted abuse, high enough that one
# social worker filling in five referrals for a family can complete the
# task without hitting the wall. A public library NAT IP serving many
# workers may exceed this — the PR description should call that out.
_RATE_LIMIT_MAX = 5
_RATE_LIMIT_WINDOW_SECONDS = 60 * 60
_RATE_LIMIT_CACHE_PREFIX = "partner_referral:rl:"


def _client_ip(request) -> str:
    """Best-effort caller IP for rate-limit bucketing.

    ``REMOTE_ADDR`` is the safe default — ``X-Forwarded-For`` is only
    trustworthy when the proxy in front of Django is known to strip
    client-supplied values, which is not the case here.
    """
    return request.META.get("REMOTE_ADDR") or "unknown"


def _rate_limit_exceeded(request) -> bool:
    """Increment the per-IP counter and return True when we are over
    the limit for the current hour-long window."""
    ip = _client_ip(request)
    key = f"{_RATE_LIMIT_CACHE_PREFIX}{ip}"

    # ``cache.add`` is atomic with the LocMemCache default; it only
    # sets the value (and the TTL) if the key does not already exist,
    # which gives us the "hour starts at the first submission" window.
    cache.add(key, 0, timeout=_RATE_LIMIT_WINDOW_SECONDS)
    try:
        current = cache.incr(key)
    except ValueError:
        # Key expired between add and incr; restart the window.
        cache.set(key, 1, timeout=_RATE_LIMIT_WINDOW_SECONDS)
        current = 1
    return current > _RATE_LIMIT_MAX


@require_http_methods(["GET", "POST"])
def partner_referral_form(request):
    if request.method == "POST" and _rate_limit_exceeded(request):
        # 429 is the correct status for a rate-limited POST. The
        # honeypot branch below handles bots silently; this branch is
        # for genuine humans who are submitting too fast.
        return HttpResponse(
            "Too many submissions from your network — please try again "
            "in an hour.",
            status=429,
            content_type="text/plain; charset=utf-8",
        )

    form = PartnerReferralForm(request.POST or None)

    if request.method == "POST":
        # Honeypot first — bail BEFORE form validation so we don't
        # leak which fields failed. A 302 to the thank-you page keeps
        # the trap invisible to the bot.
        if form.is_bot:
            return redirect(reverse("partner_referral_thanks"))

        if form.is_valid():
            partner = form.cleaned_data["partner_id"]
            data = form.cleaned_data
            app = create_partner_referral(
                partner=partner,
                partner_contact_name=data["partner_contact_name"],
                partner_contact_email=data["partner_contact_email"],
                member_full_name=data["member_full_name"],
                member_email=data.get("member_email", ""),
                member_dob=data["member_dob"],
                member_phone=data.get("member_phone"),
            )
            return redirect(
                reverse("partner_referral_thanks") + f"?ref={app.id}"
            )

    return render(
        request,
        "accounts/application/partner_referral.html",
        {"form": form},
    )


@require_http_methods(["GET"])
def partner_referral_thanks(request):
    return render(
        request,
        "accounts/application/partner_referral_thanks.html",
        {"ref": request.GET.get("ref", "")},
    )
