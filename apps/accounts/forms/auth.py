from django import forms


class EmailLoginForm(forms.Form):
    """HTML form for the login screen. Format validation only —
    credential check lives in apps.accounts.services.auth.sign_in.
    """

    email = forms.EmailField(
        widget=forms.EmailInput(
            attrs={
                "autofocus": True,
                "autocomplete": "email",
                "inputmode": "email",
                "class": "input",
                "placeholder": "you@example.com",
            }
        )
    )
    password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                "autocomplete": "current-password",
                "class": "input",
                "placeholder": "Password",
            }
        )
    )
