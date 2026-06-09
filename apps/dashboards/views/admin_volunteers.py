"""Admin volunteers directory (Story 12.13).

Mirrors the members CRUD shape so the two pages share visual and
mental model: list/detail/deactivate/reactivate. Detail surfaces the
volunteer's availability grid and recent delivery success rate.
"""
from django.contrib import messages
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from apps.accounts.models import User
from apps.accounts.services.users import deactivate_user, reactivate_user
from apps.core.decorators import role_required
from apps.dashboards.services.admin_volunteers import (
    VolunteerSearchFilters,
    get_volunteer_detail,
    search_volunteers,
)


@role_required("admin")
def admin_volunteers_list(request):
    filters = VolunteerSearchFilters(
        q=request.GET.get("q", "").strip(),
        status=request.GET.get("status", "").strip(),
    )
    try:
        page_num = int(request.GET.get("page") or 1)
    except (TypeError, ValueError):
        page_num = 1

    result = search_volunteers(filters, page=page_num)

    base_params = request.GET.copy()
    base_params.pop("page", None)

    return render(
        request,
        "dashboards/admin/volunteers_list.html",
        {
            "active": "home",
            "page_title": "Volunteers",
            "page": result["page"],
            "filters": result["filters"],
            "total": result["total"],
            "base_querystring": base_params.urlencode(),
        },
    )


@role_required("admin")
def admin_volunteer_detail(request, pk: int):
    detail = get_volunteer_detail(pk)
    if detail is None:
        raise Http404("Volunteer not found")
    return render(
        request,
        "dashboards/admin/volunteer_detail.html",
        {
            "active": "home",
            "page_title": detail["volunteer"].full_name,
            **detail,
        },
    )


@require_POST
@role_required("admin")
def admin_volunteer_deactivate(request, pk: int):
    volunteer = get_object_or_404(User, pk=pk, role="volunteer")
    deactivate_user(volunteer, request.user)
    messages.success(request, f"Deactivated {volunteer.full_name}.")
    return redirect(reverse("dashboards:admin_volunteer_detail", args=[volunteer.id]))


@require_POST
@role_required("admin")
def admin_volunteer_reactivate(request, pk: int):
    volunteer = get_object_or_404(User, pk=pk, role="volunteer")
    reactivate_user(volunteer, request.user)
    messages.success(request, f"Reactivated {volunteer.full_name}.")
    return redirect(reverse("dashboards:admin_volunteer_detail", args=[volunteer.id]))
