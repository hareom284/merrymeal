"""Admin weekly-planner grid + HTMX cell-edit views (Story 3.3)."""

from __future__ import annotations

import datetime as dt

from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404, render
from django.utils import timezone

from apps.core.decorators import role_required
from apps.kitchens.models import Kitchen
from apps.planning.forms.planner import MealPlanCellForm
from apps.planning.models import MealPlan
from apps.planning.services.coverage import acknowledge, diet_warnings
from apps.planning.services.planner import upsert_cell


def _monday_of(d: dt.date) -> dt.date:
    """Return the Monday of the week containing ``d``."""
    return d - dt.timedelta(days=d.weekday())


def _parse_week(raw: str | None) -> dt.date:
    """Parse the ``?week=YYYY-MM-DD`` query param.

    Defaults to *next* Monday when ``raw`` is falsy (story acceptance criterion).
    Raises ``ValueError`` for malformed input — the caller converts that to a 400.
    """
    if not raw:
        today = timezone.localdate()
        return _monday_of(today) + dt.timedelta(days=7)
    try:
        return _monday_of(dt.date.fromisoformat(raw))
    except ValueError as exc:
        raise ValueError(f"invalid week: {raw!r}") from exc


@role_required("admin")
def planner_view(request):
    """Render the (kitchen × day) grid for the selected week."""
    try:
        monday = _parse_week(request.GET.get("week"))
    except ValueError as exc:
        return HttpResponseBadRequest(str(exc))

    days = [monday + dt.timedelta(days=i) for i in range(7)]
    kitchens = list(Kitchen.objects.order_by("name"))
    plans = (
        MealPlan.objects
        .filter(service_date__gte=days[0], service_date__lte=days[-1])
        .select_related("meal", "kitchen")
    )
    by_cell = {(p.kitchen_id, p.service_date): p for p in plans}
    warnings_by_plan = {p.id: diet_warnings(p) for p in plans}
    grid = [
        {
            "kitchen": k,
            "cells": [
                {
                    "date": d,
                    "plan": by_cell.get((k.id, d)),
                    "warnings": (
                        warnings_by_plan.get(by_cell[(k.id, d)].id, {})
                        if (k.id, d) in by_cell
                        else {}
                    ),
                }
                for d in days
            ],
        }
        for k in kitchens
    ]
    return render(
        request,
        "planning/admin/planner.html",
        {
            "monday": monday,
            "days": days,
            "grid": grid,
            "prev_week": (monday - dt.timedelta(days=7)).isoformat(),
            "next_week": (monday + dt.timedelta(days=7)).isoformat(),
        },
    )


@role_required("admin")
def cell_edit_view(request):
    """GET → modal partial. POST → upsert + cell partial (HTMX swap)."""
    raw_kitchen = request.GET.get("kitchen") or request.POST.get("kitchen")
    raw_date = request.GET.get("date") or request.POST.get("date")
    try:
        kitchen_id = int(raw_kitchen)
        service_date = dt.date.fromisoformat(raw_date)
    except (TypeError, ValueError):
        return HttpResponseBadRequest("bad kitchen/date")

    kitchen = get_object_or_404(Kitchen, pk=kitchen_id)

    if request.method == "POST":
        form = MealPlanCellForm(request.POST)
        if form.is_valid():
            plan = upsert_cell(
                kitchen=kitchen,
                meal=form.cleaned_data["meal"],
                service_date=service_date,
                planned_quantity=form.cleaned_data["planned_quantity"],
                published_by=request.user,
            )
            return render(
                request,
                "planning/admin/_cell.html",
                {
                    "kitchen": kitchen,
                    "date": service_date,
                    "plan": plan,
                    "cell": {
                        "date": service_date,
                        "plan": plan,
                        "warnings": diet_warnings(plan),
                    },
                },
            )
    else:
        existing = MealPlan.objects.filter(
            kitchen=kitchen, service_date=service_date
        ).first()
        form = MealPlanCellForm(
            initial={
                "meal": existing.meal_id if existing else None,
                "planned_quantity": existing.planned_quantity if existing else 20,
            }
        )
    return render(
        request,
        "planning/admin/_cell_form.html",
        {"form": form, "kitchen": kitchen, "date": service_date},
    )


@role_required("admin")
def cell_acknowledge_view(request):
    """HTMX endpoint — ack the diet-coverage warning on a single plan.

    Swaps the cell <td> back into the grid. The badge re-renders muted
    grey because ``warnings_acknowledged_by`` is now set.
    """
    if request.method != "POST":
        return HttpResponseBadRequest("POST only")
    raw_plan = request.POST.get("plan") or request.GET.get("plan")
    try:
        plan_id = int(raw_plan)
    except (TypeError, ValueError):
        return HttpResponseBadRequest("bad plan id")
    plan = get_object_or_404(MealPlan.objects.select_related("kitchen", "meal"), pk=plan_id)
    acknowledge(plan, request.user)
    return render(
        request,
        "planning/admin/_cell.html",
        {
            "kitchen": plan.kitchen,
            "date": plan.service_date,
            "plan": plan,
            "cell": {
                "date": plan.service_date,
                "plan": plan,
                "warnings": diet_warnings(plan),
            },
        },
    )
