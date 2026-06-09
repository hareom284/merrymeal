from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from apps.accounts.models import Application, City
from apps.core.decorators import role_required
from apps.dietary.models import Allergy, DietPreference


def _resolve_diet_chips(applications):
    """Attach `.dietary_chips` (list[str]) to each application in-place."""
    ids = {pid for app in applications for pid in (app.dietary_ids or [])}
    names = dict(
        DietPreference.objects.filter(id__in=ids).values_list("id", "name")
    )
    for app in applications:
        app.dietary_chips = [
            names[pid] for pid in (app.dietary_ids or []) if pid in names
        ]


def _resolve_allergy_chips(applications):
    """Attach `.allergy_chips` (list[str]) to each application in-place."""
    ids = {aid for app in applications for aid in (app.allergy_ids or [])}
    names = dict(
        Allergy.objects.filter(id__in=ids).values_list("id", "name")
    )
    for app in applications:
        app.allergy_chips = [
            names[aid] for aid in (app.allergy_ids or []) if aid in names
        ]


def _resolve_suburbs(applications):
    """Attach `.suburb` (str | None) — the City name for `city_id`."""
    ids = {app.city_id for app in applications if app.city_id}
    names = dict(City.objects.filter(id__in=ids).values_list("id", "name"))
    for app in applications:
        app.suburb = names.get(app.city_id) if app.city_id else None


@role_required("admin")
def admin_applications_list(request):
    qs = (
        Application.objects
        .filter(status=Application.STATUS_SUBMITTED)
        .order_by("-created_at", "-id")
    )

    selected_city = request.GET.get("city")
    has_allergies = request.GET.get("has_allergies") == "1"

    if selected_city:
        try:
            qs = qs.filter(city_id=int(selected_city))
        except (TypeError, ValueError):
            selected_city = ""

    if has_allergies:
        applications = [a for a in qs if a.allergy_ids]
    else:
        applications = list(qs)

    _resolve_suburbs(applications)
    _resolve_diet_chips(applications)
    _resolve_allergy_chips(applications)

    context = {
        "applications": applications,
        "cities": list(City.objects.order_by("name")),
        "selected_city": int(selected_city) if selected_city else None,
        "has_allergies": has_allergies,
        "active": "applications",
        "page_title": "Applications",
    }
    return render(
        request, "dashboards/admin/applications_list.html", context
    )


@role_required("admin")
def admin_application_detail(request, pk: int):
    application = get_object_or_404(Application, pk=pk)
    suburb = (
        City.objects.filter(pk=application.city_id).values_list("name", flat=True).first()
        if application.city_id else None
    )
    diet_chips = list(
        DietPreference.objects
        .filter(id__in=application.dietary_ids or [])
        .values_list("name", flat=True)
    )
    allergy_chips = list(
        Allergy.objects
        .filter(id__in=application.allergy_ids or [])
        .values_list("name", flat=True)
    )
    return render(
        request,
        "dashboards/admin/application_detail.html",
        {
            "application": application,
            "suburb": suburb,
            "diet_chips": diet_chips,
            "allergy_chips": allergy_chips,
            "reject_error": request.GET.get("reject_error", ""),
            "active": "applications",
            "page_title": application.full_name,
        },
    )


@role_required("admin")
@require_POST
def admin_application_approve(request, pk: int):
    from apps.accounts.services.applications import approve_application

    application = get_object_or_404(Application, pk=pk)
    try:
        approve_application(application, request.user)
    except ValueError as exc:
        messages.error(request, str(exc))
        return redirect(
            reverse("dashboards:admin_application_detail", args=[application.id])
        )
    messages.success(request, f"Approved {application.full_name}.")
    return redirect(reverse("dashboards:admin_applications"))


@role_required("admin")
@require_POST
def admin_application_reject(request, pk: int):
    from apps.accounts.services.applications import reject_application

    application = get_object_or_404(Application, pk=pk)
    reason = (request.POST.get("reason") or "").strip()
    if not reason:
        suburb = (
            City.objects.filter(pk=application.city_id).values_list("name", flat=True).first()
            if application.city_id else None
        )
        return render(
            request,
            "dashboards/admin/application_detail.html",
            {
                "application": application,
                "suburb": suburb,
                "diet_chips": [],
                "allergy_chips": [],
                "reject_error": "Please provide a reason.",
                "active": "applications",
                "page_title": application.full_name,
            },
            status=200,
        )

    try:
        reject_application(application, request.user, reason=reason)
    except ValueError as exc:
        messages.error(request, str(exc))
        return redirect(
            reverse("dashboards:admin_application_detail", args=[application.id])
        )
    messages.success(request, f"Rejected {application.full_name}.")
    return redirect(reverse("dashboards:admin_applications"))
