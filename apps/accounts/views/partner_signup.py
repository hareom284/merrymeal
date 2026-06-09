"""Public partner-org signup form view.

Lives at ``/apply-partner/``. Intentionally unauthenticated so a
prospective partner charity / clinician can register their org
without needing a MerryMeal account first.

Submissions land as ``Application`` rows tagged with
``metadata["kind"] == "partner_signup"`` for admin triage. See the
note on ``apps.accounts.services.applications.create_partner_signup``
for why the application table is the inbox (locked Partner schema
has no status / contact columns).
"""

from __future__ import annotations

from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from apps.accounts.forms.partner_signup import PartnerSignupForm
from apps.accounts.services.applications import create_partner_signup


@require_http_methods(["GET", "POST"])
def partner_signup_form(request):
    form = PartnerSignupForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        data = form.cleaned_data
        create_partner_signup(
            org_legal_name=data["org_legal_name"],
            org_type=data["org_type"],
            contact_name=data["contact_name"],
            contact_email=data["contact_email"],
            contact_phone=data.get("contact_phone", ""),
            message=data.get("message", ""),
        )
        return redirect(reverse("partner_signup_thanks"))

    return render(
        request,
        "accounts/partner_signup/form.html",
        {"form": form},
    )


@require_http_methods(["GET"])
def partner_signup_thanks(request):
    return render(request, "accounts/partner_signup/thanks.html", {})
