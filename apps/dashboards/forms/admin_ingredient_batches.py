"""Admin-side form for adding an ingredient batch (Story 12.16).

A thin sibling of the kitchen-staff ``StockReceiveForm`` — same fields,
plus a kitchen picker (kitchen staff are bound to one; admins choose).
Brand-styled widgets so the form fits the admin shell without
per-template tweaks.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from django import forms

from apps.kitchens.models import Ingredient, Kitchen

_INPUT_CLASSES = (
    "w-full rounded-xl border border-warm-300 bg-white px-4 py-2.5 "
    "text-sm focus:outline-none focus:border-brand-green "
    "focus:ring-2 focus:ring-brand-green/30"
)


class AdminBatchForm(forms.Form):
    kitchen = forms.ModelChoiceField(
        queryset=Kitchen.objects.all().order_by("name"),
        widget=forms.Select(attrs={"class": _INPUT_CLASSES}),
    )
    ingredient = forms.ModelChoiceField(
        queryset=Ingredient.objects.all().order_by("name"),
        widget=forms.Select(attrs={"class": _INPUT_CLASSES}),
    )
    quantity = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=Decimal("0.01"),
        widget=forms.NumberInput(attrs={"step": "0.01", "class": _INPUT_CLASSES}),
    )
    received_at = forms.DateField(
        required=True,
        initial=date.today,
        widget=forms.DateInput(attrs={"type": "date", "class": _INPUT_CLASSES}),
    )
    expiration_date = forms.DateField(
        required=True,
        widget=forms.DateInput(attrs={"type": "date", "class": _INPUT_CLASSES}),
    )
    lot_number = forms.CharField(
        required=False,
        max_length=80,
        widget=forms.TextInput(attrs={"class": _INPUT_CLASSES}),
    )
