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

    def __init__(self, *args, exclude_volunteer_id: int | None = None, **kwargs):
        """``exclude_volunteer_id`` removes the currently-assigned volunteer
        from the dropdown so the admin can't pick a same-volunteer dead-end
        that the reassign service rejects with HTTP 400. Pass the
        delivery's current ``volunteer_id`` when rendering the modal."""
        super().__init__(*args, **kwargs)
        if exclude_volunteer_id is not None:
            self.fields["volunteer"].queryset = (
                self.fields["volunteer"].queryset.exclude(pk=exclude_volunteer_id)
            )
