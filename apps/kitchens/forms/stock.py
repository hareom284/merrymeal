from datetime import date
from decimal import Decimal

from django import forms

from apps.kitchens.models import Ingredient, Kitchen


class StockReceiveForm(forms.Form):
    kitchen = forms.ModelChoiceField(queryset=Kitchen.objects.all())
    ingredient = forms.ModelChoiceField(queryset=Ingredient.objects.all().order_by("name"))
    quantity = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=Decimal("0.01"),
    )
    received_at = forms.DateField(
        required=True,
        initial=date.today,
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    expiration_date = forms.DateField(
        required=True,
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    lot_number = forms.CharField(required=False, max_length=80)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for _name, field in self.fields.items():
            existing = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = (existing + " input").strip()

    def clean(self):
        cleaned = super().clean()
        received = cleaned.get("received_at")
        expiration = cleaned.get("expiration_date")
        if received and expiration and expiration < received:
            self.add_error(
                "expiration_date",
                "Expiration date must be on or after the received date.",
            )
        return cleaned
