"""Tests for Story 4.11 — 2-tap meal feedback (member).

Covers:
* ``apps.delivery.services.feedback.record_feedback`` — happy path +
  idempotency (a second call returns the same row, leaves the first
  rating untouched).
* ``POST /member/feedback/<delivery_id>/`` — auth/scope, status guard,
  duplicate-submit returns the "already recorded" partial.

Adaptations from the spec
-------------------------
* The factory's ``DeliveryFactory(member=...)`` keyword is the actual
  field name (the spec uses ``delivery.member_id == user.id``); we
  pass the ``User`` instance directly because the factory accepts it.
* Tags are stored as ``json.dumps({"tags": [...]})`` inside
  ``DeliveryFeedback.note`` — the model layer does not validate the
  shape so we round-trip through ``json.loads`` in the assertion.
"""
from __future__ import annotations

import json

import pytest
from django.urls import reverse

from apps.accounts.tests.factories import UserFactory
from apps.delivery.models import DeliveryFeedback
from apps.delivery.services.feedback import record_feedback
from apps.delivery.tests.factories import DeliveryFactory


@pytest.mark.django_db
def test_record_feedback_creates_row():
    d = DeliveryFactory(status="delivered")
    fb = record_feedback(d, rating=4, tags=["loved_it"])
    assert fb.rating == 4
    assert json.loads(fb.note)["tags"] == ["loved_it"]


@pytest.mark.django_db
def test_record_feedback_idempotent():
    d = DeliveryFactory(status="delivered")
    first = record_feedback(d, rating=5, tags=["great"])
    second = record_feedback(d, rating=1, tags=["bland"])
    # Second call returns the existing row unchanged.
    assert first.id == second.id
    assert second.rating == 5


@pytest.mark.django_db
def test_record_feedback_rejects_out_of_range_rating():
    d = DeliveryFactory(status="delivered")
    with pytest.raises(ValueError):
        record_feedback(d, rating=6, tags=[])
    with pytest.raises(ValueError):
        record_feedback(d, rating=0, tags=[])


@pytest.mark.django_db
def test_submit_view_creates_feedback(client):
    member = UserFactory(role="member")
    d = DeliveryFactory(status="delivered", member=member)
    client.force_login(member)
    resp = client.post(
        reverse("delivery:feedback", args=[d.id]),
        {"rating": "5", "tags": ["loved_it", "great"]},
    )
    assert resp.status_code == 200
    fb = DeliveryFeedback.objects.get(delivery=d)
    assert fb.rating == 5
    assert set(json.loads(fb.note)["tags"]) == {"loved_it", "great"}


@pytest.mark.django_db
def test_submit_view_no_tags_is_ok(client):
    """Chips are optional — a star-only submit creates a row with []."""
    member = UserFactory(role="member")
    d = DeliveryFactory(status="delivered", member=member)
    client.force_login(member)
    resp = client.post(
        reverse("delivery:feedback", args=[d.id]),
        {"rating": "3"},
    )
    assert resp.status_code == 200
    fb = DeliveryFeedback.objects.get(delivery=d)
    assert fb.rating == 3
    assert json.loads(fb.note)["tags"] == []


@pytest.mark.django_db
def test_submit_view_second_post_returns_thanks_partial(client):
    """Second submit hits the duplicate guard and renders the thanks card."""
    member = UserFactory(role="member")
    d = DeliveryFactory(status="delivered", member=member)
    client.force_login(member)
    url = reverse("delivery:feedback", args=[d.id])

    first = client.post(url, {"rating": "5", "tags": ["loved_it"]})
    assert first.status_code == 200

    second = client.post(url, {"rating": "1", "tags": ["bland"]})
    assert second.status_code == 200
    assert b"feedback-thanks" in second.content
    assert b"already recorded" in second.content

    # First feedback row is unchanged.
    fb = DeliveryFeedback.objects.get(delivery=d)
    assert fb.rating == 5


@pytest.mark.django_db
def test_submit_view_404_for_other_member(client):
    owner = UserFactory(role="member")
    intruder = UserFactory(role="member")
    d = DeliveryFactory(status="delivered", member=owner)
    client.force_login(intruder)
    resp = client.post(
        reverse("delivery:feedback", args=[d.id]),
        {"rating": "5"},
    )
    assert resp.status_code == 404


@pytest.mark.django_db
def test_submit_view_rejects_non_delivered(client):
    member = UserFactory(role="member")
    d = DeliveryFactory(status="pending", member=member)
    client.force_login(member)
    resp = client.post(
        reverse("delivery:feedback", args=[d.id]),
        {"rating": "5"},
    )
    assert resp.status_code == 400


@pytest.mark.django_db
def test_submit_view_rejects_missing_rating(client):
    member = UserFactory(role="member")
    d = DeliveryFactory(status="delivered", member=member)
    client.force_login(member)
    resp = client.post(
        reverse("delivery:feedback", args=[d.id]),
        {"tags": ["loved_it"]},
    )
    assert resp.status_code == 400


@pytest.mark.django_db
def test_submit_view_rejects_out_of_range_rating(client):
    member = UserFactory(role="member")
    d = DeliveryFactory(status="delivered", member=member)
    client.force_login(member)
    resp = client.post(
        reverse("delivery:feedback", args=[d.id]),
        {"rating": "7"},
    )
    assert resp.status_code == 400


@pytest.mark.django_db
def test_submit_view_rejects_unknown_tag(client):
    member = UserFactory(role="member")
    d = DeliveryFactory(status="delivered", member=member)
    client.force_login(member)
    resp = client.post(
        reverse("delivery:feedback", args=[d.id]),
        {"rating": "4", "tags": ["mystery_chip"]},
    )
    assert resp.status_code == 400


@pytest.mark.django_db
def test_submit_view_requires_member_role(client):
    """A volunteer (or any non-member) is forbidden, even if they own
    the row in some other capacity."""
    volunteer = UserFactory(role="volunteer")
    d = DeliveryFactory(status="delivered", member=volunteer)
    client.force_login(volunteer)
    resp = client.post(
        reverse("delivery:feedback", args=[d.id]),
        {"rating": "5"},
    )
    # ``role_required`` returns ``HttpResponseForbidden`` for non-member.
    assert resp.status_code == 403


@pytest.mark.django_db
def test_submit_view_requires_login(client):
    d = DeliveryFactory(status="delivered")
    resp = client.post(
        reverse("delivery:feedback", args=[d.id]),
        {"rating": "5"},
    )
    # `@login_required` redirects unauthenticated requests.
    assert resp.status_code in (302, 401, 403)
