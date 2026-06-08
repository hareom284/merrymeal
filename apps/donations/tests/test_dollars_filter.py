import pytest

from apps.donations.templatetags.donation_extras import dollars


def test_dollars_formats_whole_amounts():
    assert dollars(5_000_00) == "$5,000.00"


def test_dollars_formats_small_amounts():
    assert dollars(100) == "$1.00"
    assert dollars(0) == "$0.00"


def test_dollars_handles_none_as_zero():
    assert dollars(None) == "$0.00"


def test_dollars_rejects_floats():
    with pytest.raises(TypeError):
        dollars(5000.5)  # money is integer cents — floats are a bug
