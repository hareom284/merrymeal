"""Admin kitchens CRU (Story 12.17).

Builds on the existing read-only ``admin_kitchens`` list view (Story 6.1)
by adding detail / create / edit. No delete: Kitchen is PROTECTed by
``MealPlan.kitchen``, ``IngredientBatch.kitchen`` and
``FoodSafetyCheck.kitchen``, so a hard delete fails if any data refers
to it. Same contract as Partners.
"""
from django.contrib import messages
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from apps.core.decorators import role_required
from apps.dashboards.forms.admin_kitchens import KitchenForm
from apps.dashboards.services.kitchen_summary import get_summary
from apps.kitchens.models import Kitchen


@role_required("admin")
def admin_kitchens(request):
    kitchens = list(Kitchen.objects.all().order_by("name"))
    cards = [get_summary(k) for k in kitchens]
    return render(
        request,
        "dashboards/admin/kitchens.html",
        {
            "cards": cards,
            "has_kitchens": bool(kitchens),
            "active": "kitchens",
            "page_title": "Kitchens",
        },
    )


@role_required("admin")
def admin_kitchen_detail(request, pk: int):
    kitchen = Kitchen.objects.filter(pk=pk).first()
    if kitchen is None:
        raise Http404("Kitchen not found")

    # Counts visible on the detail page — admins use these to decide
    # whether a kitchen can safely have its service area shrunk.
    from apps.delivery.models import Delivery
    from apps.food_safety.models import FoodSafetyCheck
    from apps.kitchens.models import IngredientBatch
    from apps.planning.models import MealPlan

    return render(
        request,
        "dashboards/admin/kitchen_detail.html",
        {
            "active": "kitchens",
            "page_title": kitchen.name,
            "kitchen": kitchen,
            "summary": get_summary(kitchen),
            "meal_plan_count": MealPlan.objects.filter(kitchen=kitchen).count(),
            "batch_count": IngredientBatch.objects.filter(kitchen=kitchen).count(),
            "fs_check_count": FoodSafetyCheck.objects.filter(kitchen=kitchen).count(),
            "delivery_count": Delivery.objects.filter(
                meal_plan__kitchen=kitchen
            ).count(),
        },
    )


@role_required("admin")
def admin_kitchen_create(request):
    if request.method == "POST":
        form = KitchenForm(request.POST)
        if form.is_valid():
            kitchen = form.save()
            messages.success(request, f"Added {kitchen.name}.")
            return redirect(
                reverse("dashboards:admin_kitchen_detail", args=[kitchen.id])
            )
    else:
        form = KitchenForm()
    return render(
        request,
        "dashboards/admin/kitchen_form.html",
        {
            "active": "kitchens",
            "page_title": "New kitchen",
            "form": form,
            "mode": "create",
        },
    )


@role_required("admin")
def admin_kitchen_edit(request, pk: int):
    kitchen = get_object_or_404(Kitchen, pk=pk)
    if request.method == "POST":
        form = KitchenForm(request.POST, instance=kitchen)
        if form.is_valid():
            form.save()
            messages.success(request, f"Updated {kitchen.name}.")
            return redirect(
                reverse("dashboards:admin_kitchen_detail", args=[kitchen.id])
            )
    else:
        form = KitchenForm(instance=kitchen)
    return render(
        request,
        "dashboards/admin/kitchen_form.html",
        {
            "active": "kitchens",
            "page_title": f"Edit {kitchen.name}",
            "form": form,
            "kitchen": kitchen,
            "mode": "edit",
        },
    )
