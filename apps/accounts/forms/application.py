from django import forms

from apps.accounts.models import Application, User


class ApplicationContactForm(forms.Form):
    """Step 1 of the application wizard — applicant (and optionally
    caregiver) contact details.

    When ``applying_for_other`` is checked, the caregiver fields become
    required. The "member email" still has to be free of any existing
    ``users.email`` row, but the caregiver email is *allowed* to match an
    existing user — we use that as a signal that the link should attach to
    that caregiver instead of creating a new account.
    """

    full_name = forms.CharField(
        max_length=255,
        widget=forms.TextInput(
            attrs={
                "class": "input",
                "autocomplete": "name",
                "placeholder": "Margaret Whitlock",
            }
        ),
    )
    email = forms.EmailField(
        widget=forms.EmailInput(
            attrs={
                "class": "input",
                "autocomplete": "email",
                "inputmode": "email",
                "placeholder": "you@example.com",
            }
        )
    )
    dob = forms.DateField(
        widget=forms.DateInput(
            attrs={"class": "input", "type": "date", "autocomplete": "bday"}
        )
    )
    phone = forms.CharField(
        required=False,
        max_length=32,
        widget=forms.TextInput(
            attrs={
                "class": "input",
                "inputmode": "tel",
                "autocomplete": "tel",
                "placeholder": "0400 000 000",
            }
        ),
    )

    # ----- caregiver-on-behalf toggle (Story 1.10) -----
    applying_for_other = forms.BooleanField(required=False)

    caregiver_full_name = forms.CharField(
        required=False,
        max_length=255,
        widget=forms.TextInput(attrs={"class": "input", "autocomplete": "name"}),
    )
    caregiver_email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(
            attrs={
                "class": "input",
                "autocomplete": "email",
                "inputmode": "email",
            }
        ),
    )
    caregiver_phone = forms.CharField(
        required=False,
        max_length=32,
        widget=forms.TextInput(
            attrs={"class": "input", "inputmode": "tel", "autocomplete": "tel"}
        ),
    )
    relationship = forms.ChoiceField(
        required=False,
        choices=[("", "Select…")] + Application.RELATIONSHIP_CHOICES,
        widget=forms.Select(attrs={"class": "input"}),
    )

    def clean_email(self) -> str:
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account already exists for that email")
        return email

    def clean_caregiver_email(self) -> str:
        raw = self.cleaned_data.get("caregiver_email") or ""
        return raw.strip().lower()

    def clean(self):
        cleaned = super().clean()
        for_other = bool(cleaned.get("applying_for_other"))
        cleaned["applying_for_other"] = for_other

        if for_other:
            required = {
                "caregiver_full_name": "Caregiver name is required",
                "caregiver_email": "Caregiver email is required",
                "relationship": "Please select your relationship",
            }
            for field, message in required.items():
                if not cleaned.get(field):
                    self.add_error(field, message)

            care_email = cleaned.get("caregiver_email")
            if care_email and User.objects.filter(email__iexact=care_email).exists():
                cleaned["existing_caregiver"] = True
            else:
                cleaned["existing_caregiver"] = False
        else:
            for field in (
                "caregiver_full_name",
                "caregiver_email",
                "caregiver_phone",
                "relationship",
            ):
                cleaned[field] = None
            cleaned["existing_caregiver"] = False

        return cleaned


class ApplicationAddressForm(forms.Form):
    """Step 2 — delivery address (label, street, postcode, city)."""

    label = forms.CharField(
        max_length=120,
        initial="Home",
        widget=forms.TextInput(
            attrs={"class": "input", "autocomplete": "address-line1"}
        ),
    )
    street = forms.CharField(
        max_length=255,
        widget=forms.TextInput(
            attrs={
                "class": "input",
                "autocomplete": "street-address",
                "placeholder": "12 Main St",
            }
        ),
    )
    postal_code = forms.CharField(
        max_length=20,
        widget=forms.TextInput(
            attrs={
                "class": "input",
                "inputmode": "numeric",
                "autocomplete": "postal-code",
                "placeholder": "3000",
            }
        ),
    )
    city = forms.ModelChoiceField(
        queryset=None,
        widget=forms.Select(attrs={"class": "input"}),
        empty_label="Choose a city",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.accounts.models import City
        self.fields["city"].queryset = City.objects.all().order_by("name")


class ApplicationDietaryForm(forms.Form):
    """Step 3 — diet preferences + allergies, both optional multi-selects.

    The widget side (chip toggles) lives in the template via Alpine; this
    form only validates that the submitted ids are integers.
    """

    dietary_ids = forms.TypedMultipleChoiceField(
        required=False,
        coerce=int,
        choices=[],
        widget=forms.MultipleHiddenInput(),
    )
    allergy_ids = forms.TypedMultipleChoiceField(
        required=False,
        coerce=int,
        choices=[],
        widget=forms.MultipleHiddenInput(),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.dietary.models import Allergy, DietPreference
        self.fields["dietary_ids"].choices = [
            (p.id, p.name) for p in DietPreference.objects.all().order_by("name")
        ]
        self.fields["allergy_ids"].choices = [
            (a.id, a.name) for a in Allergy.objects.all().order_by("name")
        ]
