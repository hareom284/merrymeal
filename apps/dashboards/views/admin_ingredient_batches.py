"""Admin ingredient-batch browser + add-new (Story 12.16).

Three endpoints:
  /admin/stock/                 -> list (GET)
  /admin/stock/new/             -> create (GET/POST)
  /admin/stock/<pk>/            -> detail (GET)

No edit / delete by design — stock movements (deductions, write-offs)
are recorded as their own events; admins correct mistakes by recording
a new event, not by mutating history. Matches the FoodSafetyCheck
contract and the audit-first stance from the rest of the app.
"""
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.http import Http404
from django.shortcuts import redirect, render
from django.urls import reverse

from apps.core.decorators import role_required
from apps.dashboards.forms.admin_ingredient_batches import AdminBatchForm
from apps.dashboards.services.admin_ingredient_batches import (
    BatchSearchFilters,
    days_until_expiry,
    search_batches,
)
from apps.kitchens.models import Ingredient, IngredientBatch, Kitchen
from apps.kitchens.services.stock import receive_batch


def _safe_int(raw):
    if raw in (None, ""):
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


@role_required("admin")
def admin_batches_list(request):
    expiring_param = request.GET.get("expiring")
    expired_only = expiring_param == "expired"
    expiring_within = None
    if expiring_param and expiring_param != "expired":
        try:
            expiring_within = int(expiring_param)
        except (TypeError, ValueError):
            expiring_within = None

    filters = BatchSearchFilters(
        kitchen_id=_safe_int(request.GET.get("kitchen")),
        ingredient_id=_safe_int(request.GET.get("ingredient")),
        expiring_within_days=expiring_within,
        expired_only=expired_only,
    )
    try:
        page_num = int(request.GET.get("page") or 1)
    except (TypeError, ValueError):
        page_num = 1

    result = search_batches(filters, page=page_num)

    base_params = request.GET.copy()
    base_params.pop("page", None)

    return render(
        request,
        "dashboards/admin/batches_list.html",
        {
            "active": "home",
            "page_title": "Ingredient batches",
            "page": result["page"],
            "filters": result["filters"],
            "total": result["total"],
            "today": result["today"],
            "kitchens": list(Kitchen.objects.all().order_by("name")),
            "ingredients": list(Ingredient.objects.all().order_by("name")),
            "expiring_param": expiring_param or "",
            "base_querystring": base_params.urlencode(),
        },
    )


@role_required("admin")
def admin_batch_detail(request, pk: int):
    batch = (
        IngredientBatch.objects.select_related("kitchen", "ingredient")
        .filter(pk=pk)
        .first()
    )
    if batch is None:
        raise Http404("Batch not found")
    return render(
        request,
        "dashboards/admin/batch_detail.html",
        {
            "active": "home",
            "page_title": f"Batch #{batch.id}",
            "batch": batch,
            "days_to_expiry": days_until_expiry(batch),
        },
    )


@role_required("admin")
def admin_batch_create(request):
    if request.method == "POST":
        form = AdminBatchForm(request.POST)
        if form.is_valid():
            try:
                batch = receive_batch(
                    user=request.user,
                    kitchen=form.cleaned_data["kitchen"],
                    ingredient=form.cleaned_data["ingredient"],
                    quantity=form.cleaned_data["quantity"],
                    expiration_date=form.cleaned_data["expiration_date"],
                    received_at=form.cleaned_data["received_at"],
                    lot_number=form.cleaned_data.get("lot_number") or None,
                )
            except ValidationError as exc:
                # receive_batch calls full_clean(); flatten the message
                # dict to a single non-field error the admin can act on.
                form.add_error(None, "; ".join(
                    str(m) for messages_ in exc.message_dict.values() for m in messages_
                ))
            else:
                messages.success(
                    request,
                    f"Recorded {batch.quantity} of {batch.ingredient.name} "
                    f"at {batch.kitchen.name}.",
                )
                return redirect(reverse("dashboards:admin_batch_detail", args=[batch.id]))
    else:
        form = AdminBatchForm()

    return render(
        request,
        "dashboards/admin/batch_form.html",
        {
            "active": "home",
            "page_title": "New ingredient batch",
            "form": form,
        },
    )
