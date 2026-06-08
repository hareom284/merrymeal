"""Tests for the caregiver-alert pipeline (Story 4.13).

Covers
------
* The SMS facade picks the right backend by ``settings.SMS_BACKEND`` and
  raises on unknown values.
* A ``Delivery`` flipping to ``failed`` enqueues the django-q2 task and,
  with ``Q_CLUSTER["sync"]=True`` from ``config.settings.test``, the
  task runs inline so we can assert against ``mail.outbox`` /
  ``sms_outbox`` synchronously.
* The "no caregiver → office email, no SMS" fallback.
* The per-(member, date) SMS rate limit collapses two failures into one
  SMS but lets both emails through.
* Saves that do **not** touch ``status`` (e.g. a POD photo upload) do
  not enqueue an alert.

Phone column note
-----------------
The v1 :class:`apps.accounts.models.users.User` has no ``phone`` field
(handoff doc, Story 4.13 adaptation #2). The production service reads
phones via ``getattr(caregiver, "phone", "")``. To exercise the SMS
path in tests we attach a transient class-level ``phone`` descriptor
backed by a dict keyed on user pk — see the ``user_phone`` fixture.
"""
from __future__ import annotations

import pytest
from django.core import mail
from django.core.cache import cache
from django.test import override_settings

from apps.accounts.models import CaregiverLink
from apps.accounts.tests.factories import UserFactory
from apps.core import testing as sms_testing
from apps.core.services.sms import send_sms
from apps.delivery.services.mark_failed import mark_failed
from apps.delivery.tests.factories import DeliveryFactory


@pytest.fixture(autouse=True)
def clear_outboxes(settings):
    """Reset every shared piece of state between cases.

    ``mail.outbox`` is per-process, ``sms_outbox`` is module-level, and
    the alert pipeline relies on ``django.core.cache`` for both the
    per-delivery dedupe key and the per-(member, date) rate limit. Wipe
    all three.
    """
    settings.SMS_BACKEND = "console"
    settings.OFFICE_ALERT_EMAIL = "office@merrymeal.org"
    mail.outbox.clear()
    sms_testing.sms_outbox.clear()
    cache.clear()


@pytest.fixture
def user_phone():
    """Attach a writable ``phone`` attribute to ``User`` for the test.

    Yields a setter ``user_phone(user, number)``. The descriptor is
    installed on the class so the value survives ORM refetch — the
    django-q2 worker re-queries the delivery by pk and would otherwise
    read a fresh :class:`User` instance with no phone attached.
    """
    from apps.accounts.models import User

    storage: dict[int, str] = {}

    def _get(self):
        return storage.get(self.pk, "")

    def _set(self, value):
        storage[self.pk] = value

    descriptor = property(_get, _set)
    User.phone = descriptor  # type: ignore[attr-defined]
    try:
        yield lambda user, number: storage.__setitem__(user.pk, number)
    finally:
        del User.phone  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# SMS facade — backend resolution.
# ---------------------------------------------------------------------------


@override_settings(SMS_BACKEND="console")
def test_console_sms_records_to_outbox():
    send_sms(to="+61400000000", body="hello")
    assert sms_testing.sms_outbox == [
        {"to": "+61400000000", "body": "hello"}
    ]


@override_settings(SMS_BACKEND="invalid")
def test_invalid_backend_raises():
    with pytest.raises(ValueError):
        send_sms(to="+61", body="x")


# ---------------------------------------------------------------------------
# Signal → task → alert pipeline.
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_failure_sends_email_and_sms_to_caregiver(user_phone):
    caregiver = UserFactory(role="caregiver", email="d@x.com")
    user_phone(caregiver, "+61400000001")
    member = UserFactory(role="member")
    CaregiverLink.objects.create(
        member=member, caregiver=caregiver, relationship="family"
    )

    delivery = DeliveryFactory(status="pending", member=member)
    mark_failed(delivery, reason="no_answer", notes="")

    assert any(m.to == ["d@x.com"] for m in mail.outbox)
    assert any(
        s["to"] == "+61400000001" for s in sms_testing.sms_outbox
    )
    # Email subject uses the member's full_name (User has no
    # first_name / last_name in v1).
    sent = next(m for m in mail.outbox if m.to == ["d@x.com"])
    assert member.full_name in sent.subject


@pytest.mark.django_db
def test_no_caregiver_falls_back_to_office():
    member = UserFactory(role="member")
    delivery = DeliveryFactory(status="pending", member=member)
    mark_failed(delivery, reason="address_wrong", notes="")

    assert any(
        m.to == ["office@merrymeal.org"] for m in mail.outbox
    )
    # The office never gets an SMS — _recipients() yields phone=None
    # for the fallback branch.
    assert sms_testing.sms_outbox == []


@pytest.mark.django_db
def test_second_failure_same_day_skips_sms_but_still_emails(user_phone):
    cg = UserFactory(role="caregiver", email="d@x.com")
    user_phone(cg, "+61400000001")
    member = UserFactory(role="member")
    CaregiverLink.objects.create(
        member=member, caregiver=cg, relationship="family"
    )

    import datetime as dt

    today = dt.date.today()
    d1 = DeliveryFactory(
        status="pending", member=member, scheduled_date=today
    )
    d2 = DeliveryFactory(
        status="pending", member=member, scheduled_date=today
    )
    mark_failed(d1, reason="no_answer", notes="")
    mark_failed(d2, reason="not_home", notes="")

    # Both emails go out; only one SMS (rate-limited per member+date).
    caregiver_emails = [m for m in mail.outbox if m.to == ["d@x.com"]]
    assert len(caregiver_emails) == 2
    assert len(sms_testing.sms_outbox) == 1


@pytest.mark.django_db
def test_signal_does_not_fire_on_unrelated_save():
    delivery = DeliveryFactory(status="pending")
    delivery.photo = "http://example.com/x.jpg"
    # update_fields excludes "status" → signal handler returns early.
    delivery.save(update_fields=["photo", "updated_at"])
    assert mail.outbox == []
    assert sms_testing.sms_outbox == []


@pytest.mark.django_db
def test_email_template_renders_member_name_and_reason(user_phone):
    cg = UserFactory(role="caregiver", email="d@x.com")
    user_phone(cg, "+61400000001")
    member = UserFactory(role="member", full_name="Margaret Smith")
    CaregiverLink.objects.create(
        member=member, caregiver=cg, relationship="family"
    )
    delivery = DeliveryFactory(status="pending", member=member)
    mark_failed(delivery, reason="no_answer", notes="left voicemail")

    sent = next(m for m in mail.outbox if m.to == ["d@x.com"])
    # The bare reason slug (not "no_answer: left voicemail") should
    # appear in the plaintext body — the service splits on ":" before
    # passing to the template.
    assert "Margaret Smith" in sent.body
    assert "no_answer" in sent.body
    assert "left voicemail" not in sent.body
    # Office phone fallback default from settings is rendered in the
    # body.
    assert "03 9000 0000" in sent.body
