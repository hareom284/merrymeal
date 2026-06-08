"""Story 4.10 — Mark-failed reason form.

A thin ``forms.Form`` (not a ``ModelForm``) because ``failure_reason``
is a single ``TextField`` on :class:`Delivery` shaped server-side by
``apps.delivery.services.mark_failed`` as ``"<slug>"`` or
``"<slug>: <notes>"``. The form's only job is to constrain the four
volunteer-visible reason chips and cap free-text notes at 500 chars.

The reason slugs live here, not on the model, because they describe
**UI labels** the volunteer chooses between — not a domain enum. Epic
06 reporting will group by slug, so the values must stay stable; the
slugs are deliberately not translated.
"""
from __future__ import annotations

from django import forms

#: Reason slugs surfaced as radio chips on the "Couldn't deliver"
#: bottom sheet. Order matches the template grid (left-to-right,
#: top-to-bottom on a 2-column layout). Keep stable for Epic 06.
REASON_CHOICES = [
    ("not_home", "Not home"),
    ("no_answer", "No answer"),
    ("refused", "Refused"),
    ("address_wrong", "Address wrong"),
]


class MarkFailedForm(forms.Form):
    """Validate a mark-failed POST: exactly one ``reason`` slug + notes.

    ``reason`` is required so a radio group with nothing checked (the
    browser omits the key entirely) is rejected at ``is_valid()`` time
    — the view returns 400 instead of silently flipping the row.
    """

    reason = forms.ChoiceField(choices=REASON_CHOICES, required=True)
    notes = forms.CharField(
        required=False, max_length=500, widget=forms.Textarea
    )
