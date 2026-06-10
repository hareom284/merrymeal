from django import forms
from django.contrib.auth.password_validation import validate_password


class SetPasswordForm(forms.Form):
    """Form for the welcome `/accounts/set-password/` screen.

    Format validation only — token consume + ``user.set_password`` happen
    in the view. We run ``validate_password`` against ``self.user`` so
    Django's ``UserAttributeSimilarityValidator`` can reject passwords
    that look like the member's email / full name.
    """

    password1 = forms.CharField(
        label="New password",
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                "autocomplete": "new-password",
                "autofocus": True,
                "class": "input",
                "placeholder": "At least 8 characters",
            }
        ),
    )
    password2 = forms.CharField(
        label="Confirm password",
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                "autocomplete": "new-password",
                "class": "input",
                "placeholder": "Type it again",
            }
        ),
    )

    def __init__(self, *args, user=None, **kwargs):
        # `user` lets UserAttributeSimilarityValidator compare the chosen
        # password against the member's email + full_name.
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_password1(self):
        pw = self.cleaned_data["password1"]
        validate_password(pw, user=self.user)
        return pw

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get("password1")
        p2 = cleaned.get("password2")
        if p1 and p2 and p1 != p2:
            self.add_error("password2", "Passwords don't match.")
        return cleaned
