import pytest
from django.db import IntegrityError

from apps.donations.models import Donation
from apps.donations.tests.factories import CampaignFactory, DonationFactory


@pytest.mark.django_db
def test_donation_stores_amount_in_integer_cents():
    d = DonationFactory(amount_cents=50_00)
    assert d.amount_cents == 5000
    assert isinstance(d.amount_cents, int)


@pytest.mark.django_db
def test_donation_status_defaults_to_pending():
    d = DonationFactory()
    assert d.status == "pending"


@pytest.mark.django_db
def test_transaction_id_must_be_unique():
    campaign = CampaignFactory()
    Donation.objects.create(
        campaign=campaign,
        donor_email="a@x.com",
        amount_cents=100,
        payment_type="card",
        status="completed",
        transaction_id="cs_test_123",
    )
    with pytest.raises(IntegrityError):
        Donation.objects.create(
            campaign=campaign,
            donor_email="b@x.com",
            amount_cents=100,
            payment_type="card",
            status="completed",
            transaction_id="cs_test_123",
        )


@pytest.mark.django_db
def test_status_choices_include_cancelled_for_subscriptions():
    valid = {c[0] for c in Donation._meta.get_field("status").choices}
    assert {"pending", "completed", "failed", "refunded", "cancelled"} <= valid


@pytest.mark.django_db
def test_donor_id_is_nullable_for_anonymous_donations():
    """The schema declares ``donor_id NOT NULL`` but the public donate page
    accepts anonymous gifts — donor identity is captured via
    ``donor_email`` instead. Documented divergence in Story 5.2.
    """
    d = DonationFactory(donor_id=None)
    d.refresh_from_db()
    assert d.donor_id is None
