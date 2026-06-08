"""Tests for Story 6.7 — public partner referral form.

The form lives at ``/partners/refer/``. It is **public** (no login
required) so a social worker at a referring charity can submit a member
on behalf of their client. The submission creates an
``Application(status='submitted')`` tagged with the selected partner so
that on admin approval (Story 1.7 flow), the resulting ``User`` carries
the same ``partner_id`` — which Story 6.2's retention count then picks
up.
"""

from __future__ import annotations

import pytest
from django.core.cache import cache
from django.urls import reverse

from apps.accounts.tests.factories import UserFactory
from apps.partners.tests.factories import PartnerFactory


@pytest.fixture(autouse=True)
def _clear_rate_limit_cache():
    """Reset the rate-limit counters between tests so unrelated cases do
    not bleed into each other."""

    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def charity_partner(db):
    return PartnerFactory(
        legal_name="Northcote Community Centre", type="charity"
    )


@pytest.fixture
def other_charity(db):
    return PartnerFactory(legal_name="Aardvark Aid", type="charity")


@pytest.fixture
def restaurant_partner(db):
    return PartnerFactory(legal_name="Pizza Co", type="restaurant")


def _valid_payload(partner_id):
    return {
        "partner_id": str(partner_id),
        "partner_contact_name": "Sam Worker",
        "partner_contact_email": "sw@northcote.org",
        "member_full_name": "Margaret Example",
        "member_email": "margaret@example.com",
        "member_dob": "1948-03-12",
        "member_phone": "0400 000 000",
        "website": "",  # honeypot empty
    }


@pytest.mark.django_db
class TestPartnerReferralForm:
    def test_get_is_public(self, client):
        response = client.get(reverse("partner_referral_form"))
        assert response.status_code == 200
        assert b"Your organisation" in response.content

    def test_dropdown_lists_only_charity_partners(
        self, client, charity_partner, restaurant_partner
    ):
        response = client.get(reverse("partner_referral_form"))
        body = response.content.decode()
        assert "Northcote Community Centre" in body
        assert "Pizza Co" not in body

    def test_dropdown_is_alphabetical_by_legal_name(
        self, client, charity_partner, other_charity
    ):
        response = client.get(reverse("partner_referral_form"))
        body = response.content.decode()
        # "Aardvark Aid" should appear before "Northcote Community Centre"
        assert body.index("Aardvark Aid") < body.index(
            "Northcote Community Centre"
        )

    def test_successful_submission_creates_application(
        self, client, charity_partner
    ):
        payload = _valid_payload(charity_partner.id)
        response = client.post(reverse("partner_referral_form"), payload)
        assert response.status_code == 302
        assert reverse("partner_referral_thanks") in response["Location"]

        from apps.accounts.models import Application

        app = Application.objects.get()
        assert app.partner_id == charity_partner.id
        assert app.status == Application.STATUS_SUBMITTED
        assert app.full_name == "Margaret Example"
        assert app.email == "margaret@example.com"
        assert app.metadata["partner_contact_name"] == "Sam Worker"
        assert app.metadata["partner_contact_email"] == "sw@northcote.org"

    def test_successful_submission_redirects_with_reference(
        self, client, charity_partner
    ):
        payload = _valid_payload(charity_partner.id)
        response = client.post(reverse("partner_referral_form"), payload)
        from apps.accounts.models import Application

        app = Application.objects.get()
        assert f"ref={app.id}" in response["Location"]

    def test_honeypot_silently_succeeds_without_creating_row(
        self, client, charity_partner
    ):
        from apps.accounts.models import Application

        payload = _valid_payload(charity_partner.id) | {
            "website": "https://spam.example.com"
        }
        response = client.post(reverse("partner_referral_form"), payload)
        # We want a redirect *as if* the submission succeeded — never a
        # 4xx that would tell the bot which field triggered.
        assert response.status_code in (200, 302)
        assert Application.objects.count() == 0

    def test_missing_required_fields_returns_form_with_errors(
        self, client, charity_partner
    ):
        response = client.post(
            reverse("partner_referral_form"),
            {"partner_id": str(charity_partner.id), "website": ""},
        )
        assert response.status_code == 200
        assert b"This field is required" in response.content

    def test_restaurant_partner_id_is_rejected(
        self, client, restaurant_partner
    ):
        payload = _valid_payload(restaurant_partner.id)
        response = client.post(reverse("partner_referral_form"), payload)
        assert response.status_code == 200  # form re-rendered with errors
        from apps.accounts.models import Application

        assert Application.objects.count() == 0

    def test_csrf_token_is_present_in_form(self, client):
        response = client.get(reverse("partner_referral_form"))
        assert b"csrfmiddlewaretoken" in response.content

    def test_rate_limit_blocks_after_5_submissions_per_hour(
        self, client, charity_partner
    ):
        url = reverse("partner_referral_form")
        for _ in range(5):
            response = client.post(url, _valid_payload(charity_partner.id))
            assert response.status_code == 302
        # Sixth attempt within the hour must be blocked.
        blocked = client.post(url, _valid_payload(charity_partner.id))
        assert blocked.status_code == 429

    def test_thanks_page_renders_reference(self, client):
        url = reverse("partner_referral_thanks") + "?ref=42"
        response = client.get(url)
        assert response.status_code == 200
        assert b"42" in response.content


@pytest.mark.django_db
class TestApprovalPropagatesPartnerId:
    """Approving a partner-referral application must copy
    ``Application.partner_id`` onto the newly-minted ``User`` so
    Story 6.2's retention counts attribute the member to the correct
    referring partner.
    """

    def test_approving_application_sets_user_partner_id(
        self, charity_partner
    ):
        from apps.accounts.models import Address, Application, City
        from apps.accounts.services.applications import approve_application

        admin = UserFactory(role="admin", email="admin@merrymeal.org")
        city = City.objects.create(name="Melbourne")

        app = Application.objects.create(
            status=Application.STATUS_SUBMITTED,
            partner_id=charity_partner.id,
            full_name="Margaret Example",
            email="margaret-approval@example.com",
            dob="1948-03-12",
            address_label="Home",
            street="12 Main St",
            postal_code="3000",
            city_id=city.id,
            metadata={
                "partner_contact_name": "Sam Worker",
                "partner_contact_email": "sw@northcote.org",
            },
        )

        user = approve_application(app, admin)

        assert user.partner_id == charity_partner.id
        # Sanity-check the rest of the approval flow still works
        # (an address row was created, etc.).
        assert Address.objects.filter(user=user).count() == 1
