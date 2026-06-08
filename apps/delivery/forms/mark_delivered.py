"""Story 4.9 — POD photo upload form.

A thin ``forms.Form`` (not a ``ModelForm``) because the photo is
re-encoded + uploaded by ``apps.delivery.services.photo`` before the
URL is written back into ``Delivery.photo`` — the model has no
``ImageField`` of its own.

The geo fields are optional. The client populates them from
``navigator.geolocation``; if the user denies permission the inputs
arrive blank and the form still validates.
"""
from __future__ import annotations

from django import forms


class MarkDeliveredForm(forms.Form):
    photo = forms.ImageField(required=True)
    latitude = forms.DecimalField(
        required=False, max_digits=10, decimal_places=7
    )
    longitude = forms.DecimalField(
        required=False, max_digits=10, decimal_places=7
    )
