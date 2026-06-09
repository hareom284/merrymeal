"""Admin members directory (Story 12.11).

Four endpoints:
  /admin/members/                                 -> list (GET)
  /admin/members/<pk>/                            -> detail (GET)
  /admin/members/<pk>/deactivate/                 -> POST -> redirect
  /admin/members/<pk>/reactivate/                 -> POST -> redirect

The views are thin: forms -> service -> redirect. All the search/filter
shape lives in ``apps.dashboards.services.admin_members``; the
deactivate/reactivate transitions live in
``apps.accounts.services.users`` so the audit-log actor wrapping
stays consistent with the existing application-approval flow.
"""
from django.contrib import messages
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from apps.accounts.models import User
from apps.accounts.services.users import deactivate_member, reactivate_member
from apps.core.decorators import role_required
from apps.dashboards.services.admin_members import (
    MemberSearchFilters,
    get_member_detail,
    search_members,
)


@role_required("admin")
def admin_members_list(request):
    filters = MemberSearchFilters(
        q=request.GET.get("q", "").strip(),
        status=request.GET.get("status", "").strip(),
        partner_id=_safe_int(request.GET.get("partner")),
    )
    try:
        page_num = int(request.GET.get("page") or 1)
    except (TypeError, ValueError):
        page_num = 1

    result = search_members(filters, page=page_num)

    # Preserve active filters across pagination links without colliding
    # with the ``page`` parameter.
    base_params = request.GET.copy()
    base_params.pop("page", None)
    base_querystring = base_params.urlencode()

    return render(
        request,
        "dashboards/admin/members_list.html",
        {
            "active": "applications",
            "page_title": "Members",
            "page": result["page"],
            "filters": result["filters"],
            "total": result["total"],
            "base_querystring": base_querystring,
        },
    )


@role_required("admin")
def admin_member_detail(request, pk: int):
    detail = get_member_detail(pk)
    if detail is None:
        raise Http404("Member not found")
    return render(
        request,
        "dashboards/admin/member_detail.html",
        {
            "active": "applications",
            "page_title": detail["member"].full_name,
            **detail,
        },
    )


@require_POST
@role_required("admin")
def admin_member_deactivate(request, pk: int):
    member = get_object_or_404(User, pk=pk, role="member")
    deactivate_member(member, request.user)
    messages.success(request, f"Deactivated {member.full_name}.")
    return redirect(reverse("dashboards:admin_member_detail", args=[member.id]))


@require_POST
@role_required("admin")
def admin_member_reactivate(request, pk: int):
    member = get_object_or_404(User, pk=pk, role="member")
    reactivate_member(member, request.user)
    messages.success(request, f"Reactivated {member.full_name}.")
    return redirect(reverse("dashboards:admin_member_detail", args=[member.id]))


def _safe_int(raw):
    if raw in (None, ""):
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None
