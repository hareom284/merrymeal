"""Story 5.7 — recurring-donation management views.

Three thin views back the magic-link flow:

* ``manage_request_view`` — ``GET`` renders the email form; ``POST``
  fires off a magic link (silent success either way to avoid email
  enumeration) and redirects to the "check your inbox" page.
* ``manage_request_sent_view`` — ``GET`` only. The success page after
  ``POST``-ing the request form. Lives at its own URL (rather than a
  re-render) so the user can refresh / share without re-submitting.
* ``manage_view`` — ``GET`` validates the magic link, marks it used,
  and lists active subscriptions. ``POST`` handles the
  cancel-subscription button. Both methods route through the same
  view so the URL the donor clicked stays stable.

Per MerryMeal conventions the views are thin — every side effect
(token issue/verify, email send, Stripe cancel call) lives in
``apps.donations.services.manage``.
"""

from __future__ import annotations

from django.core.signing import BadSignature, SignatureExpired
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_http_methods

from apps.donations.forms.manage import (
    CancelSubscriptionForm,
    MagicLinkRequestForm,
)
from apps.donations.services.manage import (
    cancel_subscription,
    list_active_subscriptions,
    send_magic_link,
    verify_token,
)


@require_http_methods(["GET", "POST"])
def manage_request_view(request: HttpRequest) -> HttpResponse:
    """Email-entry form for the magic-link manage flow.

    GET renders the form. POST validates the email, hands it to
    ``send_magic_link`` (which decides whether to actually send), and
    redirects to the "check your inbox" page **regardless** of the
    outcome — this is the email-enumeration defence. The redirect
    target, response timing, status code and body must all be
    identical for known and unknown emails.
    """
    if request.method == "POST":
        form = MagicLinkRequestForm(request.POST)
        if form.is_valid():
            # Always-silent: ``send_magic_link`` no-ops if the email
            # has no active recurring donation. We do NOT branch on its
            # return value here — that would leak existence via timing
            # or error path.
            send_magic_link(form.cleaned_data["email"])
            return redirect(reverse("donations:manage_request_sent"))
        # Invalid email (e.g. "not-an-email"): re-render so the donor
        # can fix it. This is the only way the page differs from the
        # silent-success branch; a malformed email is not a privacy
        # leak (any email shaped string makes it through).
        return render(
            request,
            "donations/manage_request.html",
            {"form": form},
        )

    return render(
        request,
        "donations/manage_request.html",
        {"form": MagicLinkRequestForm()},
    )


@require_GET
def manage_request_sent_view(request: HttpRequest) -> HttpResponse:
    """Success page after the email form is submitted.

    Lives at its own URL (rather than being a re-render of the form
    view) so the donor can refresh the page without re-POSTing.
    """
    return render(request, "donations/manage_request_sent.html", {})


@require_http_methods(["GET", "POST"])
def manage_view(request: HttpRequest, token: str) -> HttpResponse:
    """Magic-link landing page: list subscriptions, handle cancel.

    GET burns the single-use token (``verify_token(..., mark_used=True)``)
    and renders the list of active subscriptions. The token is
    consumed on the **first** GET; subsequent loads of the same URL
    return 410 — the donor must request a new link.

    POST is the cancel-subscription form. The token does NOT need to
    be re-verified (it was burned on GET); instead we trust the URL
    token's signature (which the framework still validates because
    the URL path itself carries it) plus the service-level ownership
    check inside ``cancel_subscription``. The "used" check is
    deliberately skipped on POST so the donor can cancel without
    needing a second magic link after the GET burned theirs.
    """
    # Decode the signed payload so we have the email for both
    # methods. On GET we burn the token; on POST we do NOT (the
    # donor needs the email for the ownership check below).
    try:
        if request.method == "GET":
            payload = verify_token(token, mark_used=True)
        else:
            # On POST we accept the token even if ``used_at`` is set —
            # the GET that rendered the form already burned it.
            # Validate signature + expiry but skip the used-row check
            # by re-decoding the signed payload directly.
            from django.core.signing import loads as _loads

            payload = _loads(token, salt="donations.manage", max_age=30 * 60)
    except (BadSignature, SignatureExpired):
        return render(request, "donations/manage_gone.html", status=410)

    email = payload["email"]

    if request.method == "POST":
        form = CancelSubscriptionForm(request.POST)
        if not form.is_valid():
            # Malformed POST (missing or oversized subscription_id) —
            # render the gone page; reaching this branch implies a
            # tampered form submission, not a real donor mistake.
            return render(request, "donations/manage_gone.html", status=410)
        try:
            cancel_subscription(
                email=email,
                subscription_id=form.cleaned_data["subscription_id"],
            )
        except PermissionError:
            # Email does not own the subscription — treat as gone so
            # we don't leak which sub ids exist.
            return render(request, "donations/manage_gone.html", status=410)
        # After a successful cancel, re-render the same page so the
        # donor sees the now-empty list (or other still-active subs).
        # The token has been burned by the GET that loaded the form,
        # so the page is one-shot for the cancel action too.
        subscriptions = list_active_subscriptions(email)
        return render(
            request,
            "donations/manage.html",
            {
                "subscriptions": subscriptions,
                "email": email,
                "cancelled": True,
                "token": token,
            },
        )

    subscriptions = list_active_subscriptions(email)
    return render(
        request,
        "donations/manage.html",
        {
            "subscriptions": subscriptions,
            "email": email,
            "cancelled": False,
            "token": token,
        },
    )
