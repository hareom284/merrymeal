from django import forms
from django.contrib import messages
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from apps.core.decorators import role_required
from apps.food_safety.forms.check import CheckForm
from apps.food_safety.services.checks import record_check, today_checks_for
from apps.kitchens.models import Kitchen


class _KitchenChoice(forms.Form):
    kitchen = forms.ModelChoiceField(queryset=Kitchen.objects.all())


@role_required("kitchen_staff", "admin")
@require_http_methods(["GET", "POST"])
def check_view(request):
    if request.method == "POST":
        kitchen_form = _KitchenChoice(request.POST)
        form = CheckForm(request.POST)
        if kitchen_form.is_valid() and form.is_valid():
            record_check(
                kitchen=kitchen_form.cleaned_data["kitchen"],
                user=request.user,
                check_type=form.cleaned_data["check_type"],
                temperature_celsius=form.cleaned_data["temperature_celsius"],
                result=form.cleaned_data["result"] or None,
                notes=form.cleaned_data["notes"],
            )
            messages.success(request, "Saved.")
            return redirect("food_safety:safety-check")
    else:
        kitchen_form = _KitchenChoice()
        form = CheckForm(initial={"check_type": "storage_temp"})

    return render(request, "food_safety/check.html", {
        "form": form,
        "kitchen_form": kitchen_form,
        "today_rows": today_checks_for(request.user),
    })
