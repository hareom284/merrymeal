"""Tests for the ``meals_for`` template filter.

Templates should be forgiving — bad input returns 0 rather than raising
and crashing the whole page. The strict variant (raising for floats /
negatives) is the service layer; the filter is the relaxed wrapper.
"""
from apps.donations.templatetags.donation_extras import meals_for


def test_meals_for_filter_basic():
    # $50 at $3/meal = 16 (floor).
    assert meals_for(5000) == 16


def test_meals_for_filter_handles_none():
    # ``{{ donation.amount_cents|meals_for }}`` against an unset amount
    # should render "0", not blow up the page.
    assert meals_for(None) == 0


def test_meals_for_filter_handles_empty_string():
    # Templates pass missing context keys as empty strings under some
    # backends — must not raise.
    assert meals_for("") == 0


def test_meals_for_filter_coerces_string_digits():
    # Django passes filter arguments through as strings in
    # ``{{ chip|add:"00"|meals_for }}``. The filter must accept a
    # digit-string and floor-convert it.
    assert meals_for("5000") == 16


def test_meals_for_filter_swallows_bad_input():
    # A float string ("12.5") would raise from the service; the filter
    # must catch and return 0.
    assert meals_for("not-a-number") == 0
    assert meals_for(-100) == 0
