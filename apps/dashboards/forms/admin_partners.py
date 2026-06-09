"""Admin-side Partner form (Story 12.15).

Plain ``ModelForm`` over the Partner schema — just legal_name + type.
Brand-styled widgets so the rendered form fits the rest of the admin
UI without per-template tweaks.
"""
from __future__ import annotations

from django import forms

from apps.partners.models import Partner

_INPUT_CLASSES = (
    "w-full rounded-xl border border-warm-300 bg-white px-4 py-2.5 "
    "text-sm focus:outline-none focus:border-brand-green "
    "focus:ring-2 focus:ring-brand-green/30"
)


class PartnerForm(forms.ModelForm):
    class Meta:
        model = Partner
        fields = ["legal_name", "type"]
        widgets = {
            "legal_name": forms.TextInput(attrs={"class": _INPUT_CLASSES}),
            "type": forms.Select(attrs={"class": _INPUT_CLASSES}),
        }
