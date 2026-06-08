"""Smoke tests for ``DonationAdmin``.

The project does not mount Django's built-in ``admin`` URL namespace
(``config/urls.py`` only carries custom-branded admin views). So we
exercise registration + display configuration directly via the registry,
matching the convention in ``apps/kitchens/tests``.
"""

import pytest
from django.contrib.admin.sites import site

from apps.donations.admin import DonationAdmin
from apps.donations.models import Donation
from apps.donations.tests.factories import CampaignFactory, DonationFactory


class TestDonationAdminRegistration:
    def test_donation_is_registered(self):
        assert site.is_registered(Donation)

    def test_list_display_columns(self):
        admin = site._registry[Donation]
        # Story 5.2 spec — columns must be exactly these.
        for col in (
            "created_at",
            "donor_email",
            "campaign",
            "amount_display",
            "status",
            "payment_type",
            "transaction_id",
        ):
            assert col in admin.list_display, col

    def test_list_filter_columns(self):
        admin = site._registry[Donation]
        for col in ("campaign", "status", "payment_type", "is_recurring"):
            assert col in admin.list_filter, col

    def test_default_order_is_amount_desc(self):
        admin = site._registry[Donation]
        assert admin.ordering == ("-amount_cents",)

    def test_search_fields(self):
        admin = site._registry[Donation]
        assert "donor_email" in admin.search_fields
        assert "transaction_id" in admin.search_fields


@pytest.mark.django_db
class TestDonationAdminDisplays:
    def test_amount_display_renders_dollars(self):
        d = DonationFactory(amount_cents=1_234_56)
        admin = DonationAdmin(Donation, site)
        assert admin.amount_display(d) == "$1,234.56"

    def test_amount_display_ordering_is_amount_cents(self):
        """The Donation admin column must sort by the underlying integer
        column, not the formatted string. Without ``ordering=`` on the
        admin display the column wouldn't be sortable at all, which
        breaks the acceptance criterion."""
        admin = DonationAdmin(Donation, site)
        # ``admin.display`` stores the ordering hint on the bound method.
        assert getattr(admin.amount_display, "admin_order_field", None) == (
            "amount_cents"
        )

    def test_donation_appears_under_its_campaign(self):
        # End-to-end sanity: factory creates a Campaign + a Donation
        # without exploding the FK / db_column wiring.
        c = CampaignFactory(name="Winter")
        d = DonationFactory(campaign=c, amount_cents=10_00)
        d.refresh_from_db()
        assert d.campaign_id == c.id
