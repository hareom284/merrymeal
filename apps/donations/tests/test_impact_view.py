"""Tests for the donor-impact preview view.

The view is a thin GET-only page that takes an ``amount_cents`` query
parameter and renders "$X = N meals" using the same
``meals_for_amount`` service the donate-page chips, the thanks page and
the receipt email share. It exists so the donate page (Story 5.3),
thanks page (Story 5.5) and the public marketing site can link to a
canonical impact preview without duplicating the maths.
"""
import pytest
from django.test import override_settings
from django.urls import reverse


@pytest.mark.django_db
def test_impact_view_renders_meal_count_for_fifty_dollars(client):
    # $50 / $3 per meal = 16 (floor) — the canonical example from the
    # epic brief ("your $50 = 16 meals").
    response = client.get(reverse("donations:impact"), {"amount_cents": 5000})
    assert response.status_code == 200
    body = response.content.decode()
    assert "16" in body
    assert "$50.00" in body


@pytest.mark.django_db
def test_impact_view_defaults_to_zero_when_no_amount_passed(client):
    response = client.get(reverse("donations:impact"))
    assert response.status_code == 200
    body = response.content.decode()
    assert "0" in body
    assert "$0.00" in body


@pytest.mark.django_db
def test_impact_view_handles_invalid_amount_gracefully(client):
    # Bad input shouldn't 500 — the view falls back to zero so a stray
    # link from a marketing tracker doesn't crash the page.
    response = client.get(reverse("donations:impact"), {"amount_cents": "abc"})
    assert response.status_code == 200
    body = response.content.decode()
    assert "$0.00" in body


@pytest.mark.django_db
def test_impact_view_rejects_negative_amount(client):
    # Negative ``amount_cents`` is a programming error — the view falls
    # back to zero rather than rendering "-1 meals".
    response = client.get(reverse("donations:impact"), {"amount_cents": -100})
    assert response.status_code == 200
    body = response.content.decode()
    assert "$0.00" in body


@pytest.mark.django_db
@override_settings(MEAL_COST_CENTS=500)
def test_impact_view_respects_meal_cost_setting(client):
    # $50 / $5 = 10 — proves the view reads the setting at request
    # time, not at import time.
    response = client.get(reverse("donations:impact"), {"amount_cents": 5000})
    assert response.status_code == 200
    body = response.content.decode()
    assert "10" in body
