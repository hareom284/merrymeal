"""Unit tests for ``DonateForm`` (Story 5.3).

The form is the only place we cast a user-typed dollar string to integer
cents (see ``clean_amount_dollars``). These tests pin the boundary so the
rest of the donation pipeline can assume ``amount_cents`` is an ``int``.
"""

from apps.donations.forms.donate import DonateForm


def test_donate_form_accepts_chip_amount():
    form = DonateForm(
        {
            "amount_dollars": "50",
            "donor_email": "a@x.com",
            "is_recurring": "",
            "campaign_slug": "",
        }
    )
    assert form.is_valid(), form.errors
    assert form.cleaned_data["amount_cents"] == 5000


def test_donate_form_rounds_decimals_to_cents():
    form = DonateForm(
        {
            "amount_dollars": "12.34",
            "donor_email": "a@x.com",
            "is_recurring": "",
            "campaign_slug": "",
        }
    )
    assert form.is_valid()
    assert form.cleaned_data["amount_cents"] == 1234


def test_donate_form_rejects_below_minimum():
    form = DonateForm(
        {
            "amount_dollars": "0.50",
            "donor_email": "a@x.com",
            "is_recurring": "",
            "campaign_slug": "",
        }
    )
    assert not form.is_valid()
    assert "amount_dollars" in form.errors


def test_donate_form_rejects_above_maximum():
    form = DonateForm(
        {
            "amount_dollars": "10001",
            "donor_email": "a@x.com",
            "is_recurring": "",
            "campaign_slug": "",
        }
    )
    assert not form.is_valid()


def test_donate_form_requires_email():
    form = DonateForm(
        {
            "amount_dollars": "20",
            "donor_email": "",
            "is_recurring": "",
            "campaign_slug": "",
        }
    )
    assert not form.is_valid()
    assert "donor_email" in form.errors


def test_donate_form_accepts_recurring_flag():
    form = DonateForm(
        {
            "amount_dollars": "20",
            "donor_email": "a@x.com",
            "is_recurring": "on",
            "campaign_slug": "",
        }
    )
    assert form.is_valid(), form.errors
    assert form.cleaned_data["is_recurring"] is True


def test_donate_form_rejects_non_numeric_amount():
    form = DonateForm(
        {
            "amount_dollars": "twenty",
            "donor_email": "a@x.com",
            "is_recurring": "",
            "campaign_slug": "",
        }
    )
    assert not form.is_valid()
    assert "amount_dollars" in form.errors


def test_donate_form_strips_currency_symbol_and_commas():
    form = DonateForm(
        {
            "amount_dollars": "$1,250.00",
            "donor_email": "a@x.com",
            "is_recurring": "",
            "campaign_slug": "",
        }
    )
    assert form.is_valid(), form.errors
    assert form.cleaned_data["amount_cents"] == 125000
