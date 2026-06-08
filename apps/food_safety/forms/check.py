from django import forms

from apps.food_safety.models import FoodSafetyCheck
from apps.food_safety.services.checks import THRESHOLDS

_TEMP_TYPES = set(THRESHOLDS.keys())


class CheckForm(forms.Form):
    check_type = forms.ChoiceField(choices=FoodSafetyCheck.CheckType.choices)
    temperature_celsius = forms.DecimalField(
        max_digits=5, decimal_places=2, required=False,
        widget=forms.NumberInput(attrs={"step": "0.1", "class": "input h-11"}),
    )
    result = forms.ChoiceField(
        choices=[("", "—")] + list(FoodSafetyCheck.Result.choices),
        required=False,
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 3, "class": "input"}),
    )

    def clean(self):
        data = super().clean()
        check_type = data.get("check_type")
        if check_type in _TEMP_TYPES:
            if data.get("temperature_celsius") in (None, ""):
                self.add_error("temperature_celsius",
                               "Temperature is required for this check.")
            data["result"] = ""
        else:
            if data.get("result") not in {"pass", "fail"}:
                self.add_error("result", "Choose pass or fail.")
            data["temperature_celsius"] = None
        return data
