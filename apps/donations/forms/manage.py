"""Story 5.7 — forms for the recurring-donation management page.

Two tiny forms back the manage flow:

* ``MagicLinkRequestForm`` — the email-entry form on
  ``/donate/manage/``. One required ``EmailField``; the view feeds
  ``cleaned_data["email"]`` to ``send_magic_link``.
* ``CancelSubscriptionForm`` — the cancel-subscription POST. Carries
  one hidden ``subscription_id`` (the Stripe ``sub_…`` string). CSRF
  is handled by the template's ``{% csrf_token %}``; this form only
  owns the data field.

Both forms are ``forms.Form`` (not ``ModelForm``) because neither maps
to a single model row — the request form has no model at all, and the
cancel form acts on a Donation indirectly via its subscription id.
"""

from __future__ import annotations

from django import forms


class MagicLinkRequestForm(forms.Form):
    """Single-field form for the ``/donate/manage/`` email entry page."""

    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(
            attrs={
                # ``min-h-[44px]`` is the project's mobile touch-target
                # convention (see the donate page form). ``autocomplete``
                # lets the browser populate the field from saved logins.
                "class": "input min-h-[44px] w-full",
                "autocomplete": "email",
                "inputmode": "email",
                "placeholder": "you@example.com",
            }
        ),
    )


class CancelSubscriptionForm(forms.Form):
    """Cancel-subscription POST — one hidden ``subscription_id`` field."""

    # ``max_length=191`` matches ``Donation.stripe_subscription_id``.
    subscription_id = forms.CharField(
        max_length=191,
        widget=forms.HiddenInput(),
    )
