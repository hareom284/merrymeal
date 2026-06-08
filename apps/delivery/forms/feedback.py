"""Form: 2-tap feedback (Story 4.11).

The form binds the POST that the ``_feedback_card.html`` template emits:

    rating  → single value 1..5 (radio group)
    tags    → 0..N values from ``TAG_CHOICES`` (multi-checkbox)

``rating`` is required so a missing-or-blank submit fails validation —
the reviewer-pitfalls note in the story spec is explicit about this:
without ``required=True``, an empty form would pass and create a row
with ``rating=None``, which the schema technically allows but the
member never intended.

``tags`` is optional. Empty submits are valid — the JSON note becomes
``{"tags": []}`` and Epic 06 aggregations simply skip those rows when
counting tag frequencies.
"""
from __future__ import annotations

from django import forms

TAG_CHOICES: list[tuple[str, str]] = [
    ("great", "Great"),
    ("bland", "Bland"),
    ("too_cold", "Too cold"),
    ("too_small", "Too small"),
    ("loved_it", "Loved it"),
]


class FeedbackForm(forms.Form):
    rating = forms.IntegerField(
        min_value=1, max_value=5, required=True,
    )
    tags = forms.MultipleChoiceField(
        choices=TAG_CHOICES,
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )
