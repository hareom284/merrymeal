"""Admin-side form for adding a food-safety check (Story 12.12).

Different from ``apps.food_safety.forms.check.CheckForm`` because the
admin path also picks the kitchen (kitchen staff are bound to one) and
the validation is the same shape — temperature OR pass/fail depending
on check type. We don't reuse CheckForm directly so the admin can pick
the kitchen in the same form pass without a separate ``_KitchenChoice``
sibling form.
"""
from __future__ import annotations

from django import forms

from apps.food_safety.models import FoodSafetyCheck
from apps.food_safety.services.checks import THRESHOLDS
from apps.kitchens.models import Kitchen

_TEMP_TYPES = set(THRESHOLDS.keys())

# One brand class so each field renders as a rounded warm-tinted input
# without needing per-widget Tailwind tweaks in the template.
_INPUT_CLASSES = (
    "w-full rounded-xl border border-warm-300 bg-white px-4 py-2.5 "
    "text-sm focus:outline-none focus:border-brand-green "
    "focus:ring-2 focus:ring-brand-green/30"
)


class AdminFsCheckForm(forms.Form):
    kitchen = forms.ModelChoiceField(
        queryset=Kitchen.objects.all().order_by("name"),
        widget=forms.Select(attrs={"class": _INPUT_CLASSES}),
    )
    check_type = forms.ChoiceField(
        choices=FoodSafetyCheck.CheckType.choices,
        widget=forms.Select(attrs={"class": _INPUT_CLASSES}),
    )
    temperature_celsius = forms.DecimalField(
        max_digits=5, decimal_places=2, required=False,
        widget=forms.NumberInput(attrs={"step": "0.1", "class": _INPUT_CLASSES}),
    )
    result = forms.ChoiceField(
        choices=[("", "—")] + list(FoodSafetyCheck.Result.choices),
        required=False,
        widget=forms.Select(attrs={"class": _INPUT_CLASSES}),
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 3, "class": _INPUT_CLASSES}),
    )

    def clean(self):
        """Match record_check's contract — temp checks need a number,
        non-temp checks need a pass/fail manual call."""
        data = super().clean()
        check_type = data.get("check_type")
        if check_type in _TEMP_TYPES:
            if data.get("temperature_celsius") in (None, ""):
                self.add_error(
                    "temperature_celsius",
                    "Temperature is required for this check.",
                )
            data["result"] = ""
        else:
            if data.get("result") not in {"pass", "fail"}:
                self.add_error("result", "Choose pass or fail.")
            data["temperature_celsius"] = None
        return data
