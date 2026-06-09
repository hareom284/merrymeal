from django import forms

from apps.partners.models import Partner

_INPUT_CLASSES = (
    "w-full rounded-xl border border-warm-300 bg-white px-4 py-2.5 "
    "text-sm focus:outline-none focus:border-brand-green "
    "focus:ring-2 focus:ring-brand-green/30"
)
_TEXTAREA_CLASSES = _INPUT_CLASSES + " min-h-[120px]"


class PartnerSignupForm(forms.Form):
    org_legal_name = forms.CharField(
        max_length=255,
        label="Organisation legal name",
        widget=forms.TextInput(attrs={"class": _INPUT_CLASSES}),
    )
    org_type = forms.ChoiceField(
        choices=Partner.TYPE_CHOICES,
        label="Organisation type",
        widget=forms.Select(attrs={"class": _INPUT_CLASSES}),
    )
    contact_name = forms.CharField(
        max_length=255,
        label="Primary contact name",
        widget=forms.TextInput(attrs={"class": _INPUT_CLASSES}),
    )
    contact_email = forms.EmailField(
        max_length=255,
        label="Contact email",
        widget=forms.EmailInput(attrs={"class": _INPUT_CLASSES}),
    )
    contact_phone = forms.CharField(
        max_length=32,
        required=False,
        label="Contact phone (optional)",
        widget=forms.TextInput(attrs={"class": _INPUT_CLASSES}),
    )
    message = forms.CharField(
        required=False,
        label="Tell us a bit about your work (optional)",
        widget=forms.Textarea(attrs={"class": _TEXTAREA_CLASSES, "rows": 4}),
    )
