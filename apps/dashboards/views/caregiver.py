"""Caregiver dashboard views.

Story 3.8 — Caregiver multi-member view.

- `caregiver_list_view`     → one row per linked member, with today card snippet.
- `caregiver_member_detail_view` → today card for a single linked member;
   refuses any member the caregiver is not linked to (PII guard).
"""
from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, render

from apps.accounts.models import User
from apps.dashboards.services.caregiver_today import get_caregiver_summary
from apps.dashboards.services.member_today import get_today_card


def _require_role(user, role: str) -> bool:
    return user.is_authenticated and user.role == role


def _greeting_name(user) -> str:
    parts = (user.full_name or "").split()
    return parts[0] if parts else (user.email or "")


@login_required
def caregiver_list_view(request):
    if not _require_role(request.user, "caregiver"):
        return HttpResponseForbidden("caregivers only")
    summaries = get_caregiver_summary(request.user)
    return render(request, "dashboards/caregiver/list.html", {
        "summaries": summaries,
        "greeting_name": _greeting_name(request.user),
        "active": "dashboard",
        "page_title": "My members",
    })


@login_required
def caregiver_member_detail_view(request, pk: int):
    if not _require_role(request.user, "caregiver"):
        return HttpResponseForbidden("caregivers only")
    member = get_object_or_404(User, pk=pk, role="member")
    is_linked = member.caregiver_links_as_member.filter(
        caregiver=request.user
    ).exists()
    if not is_linked:
        return HttpResponseForbidden("not linked to this member")
    card = get_today_card(member)
    return render(request, "dashboards/caregiver/member_detail.html", {
        "member": member,
        "card": card,
        "active": "dashboard",
        "page_title": member.full_name,
    })
