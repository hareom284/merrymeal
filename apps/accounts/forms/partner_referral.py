"""Story 6.7 — public partner referral form.

A social worker at a referring charity fills this in on behalf of a
member. The form mirrors the Story 1.10 caregiver-on-behalf member
fields and prepends three required partner-side fields plus a honeypot.
"""

from __future__ import annotations

from django import forms

from apps.accounts.models import User
from apps.partners.models import Partner


class PartnerReferralForm(forms.Form):
    """Single-page referral form rendered at ``/partners/refer/``.

    The dropdown is restricted to ``Partner.type == 'charity'`` so
    social workers cannot accidentally pick a restaurant or corporate
    partner (which would skew Story 6.2 retention attribution).
    """

    # --- honeypot ---------------------------------------------------
    # Hidden in the template via ``class="hidden"`` so a real human
    # never fills it. Bots that auto-fill every field tip themselves
    # off here; the view treats any non-empty value as a "silent
    # success" (302 to the thank-you page so we don't reveal the trap).
    website = forms.CharField(
        required=False,
        widget=forms.HiddenInput(attrs={"autocomplete": "off"}),
    )

    # --- partner-side fields ---------------------------------------
    partner_id = forms.ModelChoiceField(
        queryset=Partner.objects.none(),  # populated in __init__
        label="Your organisation",
        empty_label="— choose your organisation —",
        widget=forms.Select(attrs={"class": "input"}),
    )
    partner_contact_name = forms.CharField(
        max_length=255,
        label="Your name",
        widget=forms.TextInput(
            attrs={"class": "input", "autocomplete": "name"}
        ),
    )
    partner_contact_email = forms.EmailField(
        label="Your email",
        widget=forms.EmailInput(
            attrs={
                "class": "input",
                "autocomplete": "email",
                "inputmode": "email",
            }
        ),
    )

    # --- member-side fields (mirror of Story 1.10 step 1) ----------
    member_full_name = forms.CharField(
        max_length=255,
        label="Member's full name",
        widget=forms.TextInput(
            attrs={
                "class": "input",
                "autocomplete": "name",
                "placeholder": "Margaret Whitlock",
            }
        ),
    )
    member_email = forms.EmailField(
        required=False,
        label="Member's email (optional)",
        widget=forms.EmailInput(
            attrs={
                "class": "input",
                "autocomplete": "email",
                "inputmode": "email",
            }
        ),
    )
    member_dob = forms.DateField(
        label="Member's date of birth",
        widget=forms.DateInput(
            attrs={
                "class": "input",
                "type": "date",
                "autocomplete": "bday",
            }
        ),
    )
    member_phone = forms.CharField(
        required=False,
        max_length=32,
        label="Member's phone (optional)",
        widget=forms.TextInput(
            attrs={
                "class": "input",
                "inputmode": "tel",
                "autocomplete": "tel",
            }
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Refresh the queryset on every instantiation so newly-added
        # charities show up without needing a worker restart.
        self.fields["partner_id"].queryset = (
            Partner.objects.filter(type="charity").order_by("legal_name")
        )

    @property
    def is_bot(self) -> bool:
        """True if the honeypot field was filled — caller should treat
        the POST as a silent success (do **not** 4xx)."""
        return bool((self.data.get("website") or "").strip())

    def clean_member_email(self) -> str:
        email = (self.cleaned_data.get("member_email") or "").strip().lower()
        if not email:
            return ""
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(
                "An account already exists for that email"
            )
        return email

    def clean_partner_contact_email(self) -> str:
        return (
            self.cleaned_data.get("partner_contact_email") or ""
        ).strip().lower()
