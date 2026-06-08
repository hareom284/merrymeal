"""Story 4.14 — ``ReassignForm``.

Single-field form that picks the new volunteer for a delivery. The
queryset is *intentionally narrow*:

* ``role='volunteer'`` — only volunteers can carry deliveries; this
  also turns the "non-volunteer rejected" rule into a hard
  ``ModelChoiceField`` constraint so the dropdown can never offer an
  invalid choice.
* ``is_active=True`` — deactivated accounts must not appear.
"""
from __future__ import annotations

from django import forms

from apps.accounts.models import User


class ReassignForm(forms.Form):
    volunteer = forms.ModelChoiceField(
        queryset=User.objects.filter(role="volunteer", is_active=True),
        required=True,
    )
