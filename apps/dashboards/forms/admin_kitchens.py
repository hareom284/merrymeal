"""Admin-side Kitchen form (Story 12.17).

ModelForm over the Kitchen schema — name, outsourced flag, lat/lng,
service radius. Lat/lng validators come from the model itself
(±90 / ±180), so the form picks them up without duplication.
"""
from __future__ import annotations

from django import forms

from apps.kitchens.models import Kitchen

_INPUT_CLASSES = (
    "w-full rounded-xl border border-warm-300 bg-white px-4 py-2.5 "
    "text-sm focus:outline-none focus:border-brand-green "
    "focus:ring-2 focus:ring-brand-green/30"
)


class KitchenForm(forms.ModelForm):
    class Meta:
        model = Kitchen
        fields = [
            "name",
            "is_outsourced",
            "latitude",
            "longitude",
            "service_radius_km",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"class": _INPUT_CLASSES}),
            "latitude": forms.NumberInput(attrs={"step": "0.0000001", "class": _INPUT_CLASSES}),
            "longitude": forms.NumberInput(attrs={"step": "0.0000001", "class": _INPUT_CLASSES}),
            "service_radius_km": forms.NumberInput(attrs={"step": "0.01", "class": _INPUT_CLASSES}),
            # is_outsourced is a checkbox — Tailwind doesn't restyle
            # native checkboxes well so we leave it plain.
        }
