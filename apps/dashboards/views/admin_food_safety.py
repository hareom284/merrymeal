"""Admin food-safety browser + add-new (Story 12.12).

Three endpoints:
  /admin/food_safety/                              -> list (GET)
  /admin/food_safety/new/                          -> create (GET/POST)
  /admin/food_safety/<pk>/                         -> detail (GET)

The list mirrors what Django's auto-admin would offer (kitchen +
result + date range filters, paginated table). The detail is read-only.
Add-new posts through ``record_check`` so the kitchen-staff capture
path and the admin path use the same audit-logged write. There is
deliberately NO edit / delete UI — food-safety records are a
compliance artefact; corrections happen via a new check that
supersedes the previous one in the audit trail.
"""
from datetime import date

from django.contrib import messages
from django.http import Http404
from django.shortcuts import redirect, render
from django.urls import reverse

from apps.core.decorators import role_required
from apps.dashboards.forms.admin_food_safety import AdminFsCheckForm
from apps.dashboards.services.admin_food_safety import (
    FsCheckFilters,
    search_checks,
)
from apps.food_safety.models import FoodSafetyCheck
from apps.food_safety.services.checks import record_check
from apps.kitchens.models import Kitchen


def _parse_date(raw: str | None) -> date | None:
    if not raw:
        return None
    try:
        return date.fromisoformat(raw)
    except ValueError:
        return None


def _safe_int(raw):
    if raw in (None, ""):
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


@role_required("admin")
def admin_fs_list(request):
    filters = FsCheckFilters(
        kitchen_id=_safe_int(request.GET.get("kitchen")),
        result=request.GET.get("result", "").strip(),
        date_from=_parse_date(request.GET.get("from")),
        date_to=_parse_date(request.GET.get("to")),
    )
    try:
        page_num = int(request.GET.get("page") or 1)
    except (TypeError, ValueError):
        page_num = 1

    result = search_checks(filters, page=page_num)

    base_params = request.GET.copy()
    base_params.pop("page", None)
    base_querystring = base_params.urlencode()

    return render(
        request,
        "dashboards/admin/food_safety_list.html",
        {
            "active": "home",
            "page_title": "Food safety",
            "page": result["page"],
            "filters": result["filters"],
            "total": result["total"],
            "kitchens": list(Kitchen.objects.all().order_by("name")),
            "base_querystring": base_querystring,
        },
    )


@role_required("admin")
def admin_fs_detail(request, pk: int):
    check = (
        FoodSafetyCheck.objects.select_related("kitchen", "checked_by", "meal_plan__meal")
        .filter(pk=pk)
        .first()
    )
    if check is None:
        raise Http404("Check not found")
    return render(
        request,
        "dashboards/admin/food_safety_detail.html",
        {
            "active": "home",
            "page_title": "Food safety check",
            "check": check,
        },
    )


@role_required("admin")
def admin_fs_create(request):
    if request.method == "POST":
        form = AdminFsCheckForm(request.POST)
        if form.is_valid():
            try:
                check = record_check(
                    kitchen=form.cleaned_data["kitchen"],
                    user=request.user,
                    check_type=form.cleaned_data["check_type"],
                    temperature_celsius=form.cleaned_data["temperature_celsius"],
                    result=form.cleaned_data["result"] or None,
                    notes=form.cleaned_data["notes"],
                )
            except ValueError as exc:
                # record_check raises if required fields are missing for
                # the chosen check type — surface that as a form error.
                form.add_error(None, str(exc))
            else:
                messages.success(
                    request,
                    f"Recorded {check.get_check_type_display()} = "
                    f"{check.get_result_display()}.",
                )
                return redirect(reverse("dashboards:admin_fs_detail", args=[check.id]))
    else:
        form = AdminFsCheckForm(initial={"check_type": "storage_temp"})

    return render(
        request,
        "dashboards/admin/food_safety_form.html",
        {
            "active": "home",
            "page_title": "New food-safety check",
            "form": form,
        },
    )
