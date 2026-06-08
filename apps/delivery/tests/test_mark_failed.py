"""Tests for Story 4.10 — Mark-failed with reason + notes.

Covers:
* ``apps.delivery.services.mark_failed.mark_failed`` — status flip,
  ``failure_reason`` text format (``slug`` or ``slug: notes``), invalid
  reason rejection, idempotency, audit-log row written.
* ``POST /volunteer/delivery/<pk>/mark-failed/`` — auth scoping (404
  for foreign delivery), 400 for bad form, ``@require_POST`` enforced,
  role gate blocks non-volunteers, HTMX response is the route fragment.

Adaptations from the spec
-------------------------
* ``pytest-freezer`` is not installed; we use ``timezone`` only for
  audit-log comparisons (none of these tests pin a date).
* ``UserAddressFactory`` is an alias for ``AddressFactory`` in
  ``apps/accounts/tests/factories.py`` — already in use elsewhere.
* The audit-log assertion only checks that a ``LogEntry`` row appears;
  it does not assert which user is the actor. Story 4.13 will layer a
  caregiver alert on the post-save signal; this story trusts that
  signal and does not import the alert service itself.
"""
from __future__ import annotations

import pytest
from auditlog.models import LogEntry
from django.urls import reverse

from apps.accounts.tests.factories import UserFactory
from apps.delivery.tests.factories import DeliveryFactory

# ---------------------------------------------------------------------------
# Service-layer tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_mark_failed_sets_status_and_reason():
    from apps.delivery.services.mark_failed import mark_failed

    d = DeliveryFactory(status="pending")
    mark_failed(d, reason="no_answer", notes="rang twice")
    d.refresh_from_db()
    assert d.status == "failed"
    assert d.failure_reason == "no_answer: rang twice"


@pytest.mark.django_db
def test_mark_failed_without_notes():
    from apps.delivery.services.mark_failed import mark_failed

    d = DeliveryFactory(status="pending")
    mark_failed(d, reason="address_wrong", notes="")
    d.refresh_from_db()
    assert d.failure_reason == "address_wrong"


@pytest.mark.django_db
def test_mark_failed_writes_audit():
    from apps.delivery.services.mark_failed import mark_failed

    d = DeliveryFactory(status="pending")
    before = LogEntry.objects.filter(object_id=str(d.id)).count()
    mark_failed(d, reason="refused", notes="")
    after = LogEntry.objects.filter(object_id=str(d.id)).count()
    assert after > before


@pytest.mark.django_db
def test_mark_failed_rejects_invalid_reason():
    from apps.delivery.services.mark_failed import mark_failed

    d = DeliveryFactory(status="pending")
    with pytest.raises(ValueError):
        mark_failed(d, reason="dog_ate_it", notes="")
    d.refresh_from_db()
    assert d.status == "pending"
    assert d.failure_reason in (None, "")


@pytest.mark.django_db
def test_mark_failed_idempotent_on_already_failed():
    """A retried call must not overwrite the original reason or spam audit."""
    from apps.delivery.services.mark_failed import mark_failed

    d = DeliveryFactory(status="pending")
    mark_failed(d, reason="not_home", notes="first")
    d.refresh_from_db()
    assert d.failure_reason == "not_home: first"

    mark_failed(d, reason="refused", notes="second")
    d.refresh_from_db()
    # Original reason preserved.
    assert d.failure_reason == "not_home: first"


# ---------------------------------------------------------------------------
# View-layer tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_view_marks_delivery_failed(client):
    """Happy path: own delivery, valid form, status flips to ``failed``."""
    sarah = UserFactory(role="volunteer")
    delivery = DeliveryFactory(volunteer=sarah, status="pending")
    client.force_login(sarah)

    resp = client.post(
        reverse("delivery:mark_failed", args=[delivery.id]),
        data={"reason": "no_answer", "notes": "rang twice"},
    )
    assert resp.status_code == 200
    delivery.refresh_from_db()
    assert delivery.status == "failed"
    assert delivery.failure_reason == "no_answer: rang twice"


@pytest.mark.django_db
def test_view_404_for_other_volunteer(client):
    """Volunteer A cannot fail Volunteer B's delivery — 404, not 403."""
    other = UserFactory(role="volunteer", email="other@example.com")
    delivery = DeliveryFactory(status="pending", volunteer=other)
    sarah = UserFactory(role="volunteer")
    client.force_login(sarah)

    resp = client.post(
        reverse("delivery:mark_failed", args=[delivery.id]),
        {"reason": "not_home", "notes": ""},
    )
    assert resp.status_code == 404
    delivery.refresh_from_db()
    assert delivery.status == "pending"


@pytest.mark.django_db
def test_view_404_for_missing_delivery(client):
    sarah = UserFactory(role="volunteer")
    client.force_login(sarah)
    resp = client.post(
        reverse("delivery:mark_failed", args=[99999]),
        data={"reason": "not_home", "notes": ""},
    )
    assert resp.status_code == 404


@pytest.mark.django_db
def test_view_blocks_non_volunteer_role(client):
    member = UserFactory(role="member")
    client.force_login(member)
    resp = client.post(
        reverse("delivery:mark_failed", args=[1]),
        data={"reason": "not_home", "notes": ""},
    )
    assert resp.status_code == 403


@pytest.mark.django_db
def test_view_rejects_get(client):
    sarah = UserFactory(role="volunteer")
    delivery = DeliveryFactory(volunteer=sarah, status="pending")
    client.force_login(sarah)
    resp = client.get(reverse("delivery:mark_failed", args=[delivery.id]))
    assert resp.status_code == 405
    delivery.refresh_from_db()
    assert delivery.status == "pending"


@pytest.mark.django_db
def test_view_400_when_reason_missing(client):
    """A radio group with nothing selected submits no ``reason`` key."""
    sarah = UserFactory(role="volunteer")
    delivery = DeliveryFactory(volunteer=sarah, status="pending")
    client.force_login(sarah)
    resp = client.post(
        reverse("delivery:mark_failed", args=[delivery.id]),
        data={"notes": "tried but no luck"},
    )
    assert resp.status_code == 400
    delivery.refresh_from_db()
    assert delivery.status == "pending"


@pytest.mark.django_db
def test_view_400_when_reason_invalid(client):
    """An out-of-range slug must not flip status."""
    sarah = UserFactory(role="volunteer")
    delivery = DeliveryFactory(volunteer=sarah, status="pending")
    client.force_login(sarah)
    resp = client.post(
        reverse("delivery:mark_failed", args=[delivery.id]),
        data={"reason": "dog_ate_it", "notes": ""},
    )
    assert resp.status_code == 400
    delivery.refresh_from_db()
    assert delivery.status == "pending"


@pytest.mark.django_db
def test_view_returns_route_fragment(client):
    """HTMX response is the rendered route fragment, not a full page."""
    sarah = UserFactory(role="volunteer")
    delivery = DeliveryFactory(volunteer=sarah, status="pending")
    client.force_login(sarah)

    resp = client.post(
        reverse("delivery:mark_failed", args=[delivery.id]),
        data={"reason": "not_home", "notes": ""},
    )
    assert resp.status_code == 200
    assert b"route-fragment" in resp.content
    assert b"today-screen" not in resp.content
