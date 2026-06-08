from datetime import timedelta
from decimal import Decimal

import pytest
from django.core import mail
from django.utils import timezone

from apps.accounts.tests.factories import UserFactory
from apps.kitchens.models import ExpiryAlertLog
from apps.kitchens.tasks.expiry_alerts import send_expiry_alerts
from apps.kitchens.tests.factories import (
    IngredientBatchFactory,
    IngredientFactory,
    KitchenFactory,
)


pytestmark = pytest.mark.django_db


def _admin():
    return UserFactory(role="admin", email="ops@merrymeal.test")


def test_one_email_per_kitchen_with_expiring_batches():
    _admin()
    today = timezone.localdate()
    a, b = KitchenFactory(name="Footscray"), KitchenFactory(name="St Kilda")
    IngredientBatchFactory(kitchen=a, ingredient=IngredientFactory(name="Rice"),
                           expiration_date=today + timedelta(days=2),
                           quantity=Decimal("3.00"))
    IngredientBatchFactory(kitchen=b, ingredient=IngredientFactory(name="Onion"),
                           expiration_date=today + timedelta(days=1),
                           quantity=Decimal("1.50"))

    send_expiry_alerts()

    assert len(mail.outbox) == 2
    subjects = {m.subject for m in mail.outbox}
    assert "Expiring batches at Footscray" in subjects
    assert "Expiring batches at St Kilda" in subjects


def test_no_email_when_no_batches():
    _admin()
    KitchenFactory()
    send_expiry_alerts()
    assert mail.outbox == []


@pytest.mark.skip(reason="ExpiryAlertLog savepoint/transaction interaction under investigation")
def test_idempotent_within_same_day():
    _admin()
    today = timezone.localdate()
    kitchen = KitchenFactory(name="Footscray")
    IngredientBatchFactory(kitchen=kitchen,
                           expiration_date=today + timedelta(days=1),
                           quantity=Decimal("2.00"))

    # First call creates the log row and sends the email.
    send_expiry_alerts()
    assert len(mail.outbox) == 1
    assert ExpiryAlertLog.objects.filter(kitchen=kitchen, sent_date=today).count() == 1

    # Second call is a no-op: IntegrityError caught internally; no second email.
    send_expiry_alerts()
    assert len(mail.outbox) == 1


def test_email_body_groups_by_ingredient():
    _admin()
    today = timezone.localdate()
    kitchen = KitchenFactory(name="Footscray")
    rice = IngredientFactory(name="Basmati rice")
    IngredientBatchFactory(kitchen=kitchen, ingredient=rice,
                           expiration_date=today + timedelta(days=1),
                           lot_number="LOT-A",
                           quantity=Decimal("2.00"))
    IngredientBatchFactory(kitchen=kitchen, ingredient=rice,
                           expiration_date=today + timedelta(days=2),
                           lot_number="LOT-B",
                           quantity=Decimal("3.00"))
    send_expiry_alerts()

    [email] = mail.outbox
    assert "Basmati rice" in email.body
    assert "LOT-A" in email.body
    assert "LOT-B" in email.body


def test_skips_kitchen_when_no_admin_user_exists(caplog):
    today = timezone.localdate()
    kitchen = KitchenFactory()
    IngredientBatchFactory(kitchen=kitchen,
                           expiration_date=today + timedelta(days=1),
                           quantity=Decimal("1.00"))
    send_expiry_alerts()
    assert mail.outbox == []
    assert any("no admin recipient" in r.message.lower() for r in caplog.records)
