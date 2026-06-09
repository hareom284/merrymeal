"""Admin partners directory (Story 12.15).

Four endpoints — full CRU (no delete; Partner is PROTECTed by
Application.partner and User.partner FKs, same problem as Kitchens.
Cleanup happens via deactivating affiliated entities).
"""
from django.contrib import messages
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from apps.core.decorators import role_required
from apps.dashboards.forms.admin_partners import PartnerForm
from apps.dashboards.services.admin_partners import (
    PartnerSearchFilters,
    get_partner_detail,
    search_partners,
)
from apps.partners.models import Partner


@role_required("admin")
def admin_partners_list(request):
    filters = PartnerSearchFilters(
        q=request.GET.get("q", "").strip(),
        type=request.GET.get("type", "").strip(),
    )
    try:
        page_num = int(request.GET.get("page") or 1)
    except (TypeError, ValueError):
        page_num = 1

    result = search_partners(filters, page=page_num)

    base_params = request.GET.copy()
    base_params.pop("page", None)

    return render(
        request,
        "dashboards/admin/partners_list.html",
        {
            "active": "home",
            "page_title": "Partners",
            "page": result["page"],
            "filters": result["filters"],
            "total": result["total"],
            "type_choices": Partner.TYPE_CHOICES,
            "base_querystring": base_params.urlencode(),
        },
    )


@role_required("admin")
def admin_partner_detail(request, pk: int):
    detail = get_partner_detail(pk)
    if detail is None:
        raise Http404("Partner not found")
    return render(
        request,
        "dashboards/admin/partner_detail.html",
        {
            "active": "home",
            "page_title": detail["partner"].legal_name,
            **detail,
        },
    )


@role_required("admin")
def admin_partner_create(request):
    if request.method == "POST":
        form = PartnerForm(request.POST)
        if form.is_valid():
            partner = form.save()
            messages.success(request, f"Added {partner.legal_name}.")
            return redirect(
                reverse("dashboards:admin_partner_detail", args=[partner.id])
            )
    else:
        form = PartnerForm()
    return render(
        request,
        "dashboards/admin/partner_form.html",
        {
            "active": "home",
            "page_title": "New partner",
            "form": form,
            "mode": "create",
        },
    )


@role_required("admin")
def admin_partner_edit(request, pk: int):
    partner = get_object_or_404(Partner, pk=pk)
    if request.method == "POST":
        form = PartnerForm(request.POST, instance=partner)
        if form.is_valid():
            form.save()
            messages.success(request, f"Updated {partner.legal_name}.")
            return redirect(
                reverse("dashboards:admin_partner_detail", args=[partner.id])
            )
    else:
        form = PartnerForm(instance=partner)
    return render(
        request,
        "dashboards/admin/partner_form.html",
        {
            "active": "home",
            "page_title": f"Edit {partner.legal_name}",
            "form": form,
            "partner": partner,
            "mode": "edit",
        },
    )
