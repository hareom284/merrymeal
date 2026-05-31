from django import forms
from django.contrib.auth import authenticate


class EmailLoginForm(forms.Form):
    email = forms.EmailField(
        widget=forms.EmailInput(
            attrs={
                "autofocus": True,
                "autocomplete": "email",
                "inputmode": "email",
                "class": "w-full rounded-xl border-2 border-stone-300 px-4 py-4 text-lg",
                "placeholder": "you@example.com",
            }
        )
    )
    password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                "autocomplete": "current-password",
                "class": "w-full rounded-xl border-2 border-stone-300 px-4 py-4 text-lg",
                "placeholder": "Password",
            }
        )
    )

    def clean(self):
        cleaned = super().clean()
        user = authenticate(email=cleaned.get("email"), password=cleaned.get("password"))
        if user is None:
            raise forms.ValidationError("Invalid email or password")
        cleaned["user"] = user
        return cleaned
