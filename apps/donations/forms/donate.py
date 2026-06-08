"""``DonateForm`` — the only place a user-typed dollar string becomes cents.

The rest of the donation pipeline (service, model, Stripe) assumes
``amount_cents`` is an integer. Doing the cast here in ``clean_amount_dollars``
keeps the boundary single-source and prevents float arithmetic from leaking
into money (see the templatetag ``dollars`` in ``donation_extras.py`` which
raises ``TypeError`` on float — the parser is the chokepoint).
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

from django import forms

# Min and max guard against fat-finger submissions. Anything above $10k must
# go through a partnerships email — the public form is for one-tap gifts.
MIN_DOLLARS = Decimal("1.00")
MAX_DOLLARS = Decimal("10000.00")


class DonateForm(forms.Form):
    """Public donate-page form.

    Hidden fields:
    * ``campaign_slug`` — set by the GET-side view when ``?campaign=`` deep
      links the user to a specific campaign; empty means "General fund".

    Visible fields:
    * ``amount_dollars`` — a free-form ``CharField``, not a ``DecimalField``,
      because chips push ``"50"`` and the custom input pushes ``"12.34"`` —
      both are normalised here. The cleaned-data side-effect is the integer
      ``amount_cents`` that downstream code consumes.
    * ``donor_email`` — required, used as the receipt destination and the
      Story 5.7 manage-subscription lookup key.
    * ``is_recurring`` — Alpine ``x-model``-bound checkbox; ``True`` flips
      the resulting Donation onto a Stripe subscription.
    """

    amount_dollars = forms.CharField(required=True)
    donor_email = forms.EmailField(required=True)
    is_recurring = forms.BooleanField(required=False)
    campaign_slug = forms.CharField(required=False, max_length=255)

    def clean_amount_dollars(self) -> str:
        """Parse the dollar string and stash ``amount_cents`` on cleaned_data.

        Returns the (stripped) raw string so the field round-trips on
        re-render after a validation error. The real downstream value is
        ``self.cleaned_data["amount_cents"]`` — an ``int``.
        """
        raw = (self.cleaned_data.get("amount_dollars") or "").strip()
        # Tolerate "$1,250.00" and "1250" alike — both are common copy-paste
        # patterns and both should resolve to 125000 cents.
        normalised = raw.lstrip("$").replace(",", "").strip()
        try:
            dollars = Decimal(normalised)
        except (InvalidOperation, ValueError) as exc:
            raise forms.ValidationError(
                "Enter a valid amount in dollars."
            ) from exc
        if dollars < MIN_DOLLARS:
            raise forms.ValidationError("Minimum donation is $1.")
        if dollars > MAX_DOLLARS:
            raise forms.ValidationError(
                "Maximum online donation is $10,000."
            )
        # ``to_integral_value()`` defaults to ROUND_HALF_EVEN — banker's
        # rounding, the right call for money even though most chip amounts
        # are integers. ``$12.345`` → ``1234`` cents.
        cents = int((dollars * 100).to_integral_value())
        self.cleaned_data["amount_cents"] = cents
        return raw
