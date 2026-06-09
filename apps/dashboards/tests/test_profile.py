"""Tests for the member-facing read-only My profile page (Story 12.4)."""
import pytest

from apps.accounts.tests.factories import (
    AddressFactory,
    MemberCaregiverLinkFactory,
    UserFactory,
)
from apps.dietary.models import Allergy, DietPreference, UserAllergy, UserDietPreference


@pytest.mark.django_db
def test_profile_requires_login(client):
    response = client.get("/profile/")
    assert response.status_code == 302


@pytest.mark.django_db
def test_profile_renders_for_authenticated_member(client):
    user = UserFactory(role="member", full_name="Margaret Chen")
    client.force_login(user)
    response = client.get("/profile/")
    assert response.status_code == 200
    assert b"Margaret Chen" in response.content


@pytest.mark.django_db
def test_profile_shows_address(client):
    user = UserFactory(role="member")
    AddressFactory(user=user, label="Home", postal_code="3000")
    client.force_login(user)
    response = client.get("/profile/")
    assert b"3000" in response.content


@pytest.mark.django_db
def test_profile_shows_diet_chips(client):
    """Diet preferences render as positive chips; the page is read-only,
    so we just assert the names appear (no checkboxes / form controls)."""
    user = UserFactory(role="member")
    pref = DietPreference.objects.create(name="Diabetic")
    UserDietPreference.objects.create(user=user, diet_preference=pref)
    client.force_login(user)
    response = client.get("/profile/")
    assert b"Diabetic" in response.content


@pytest.mark.django_db
def test_profile_shows_allergy_pills(client):
    """Allergies must be visually distinct (red) and labelled — these
    are a safety signal for kitchen + caregivers, not a soft preference."""
    user = UserFactory(role="member")
    peanut = Allergy.objects.create(name="Peanuts")
    UserAllergy.objects.create(user=user, allergy=peanut)
    client.force_login(user)
    response = client.get("/profile/")
    body = response.content
    assert b"Peanuts" in body
    assert b"Allergies" in body or b"ALLERGIES" in body


@pytest.mark.django_db
def test_profile_shows_emergency_contact_when_caregiver_linked(client):
    """First active caregiver link surfaces as the emergency contact.
    The mockup shows name + relationship; both must render."""
    member = UserFactory(role="member")
    caregiver = UserFactory(role="caregiver", full_name="Anna Lopez")
    MemberCaregiverLinkFactory(member=member, caregiver=caregiver, relationship="family")
    client.force_login(member)
    response = client.get("/profile/")
    body = response.content
    assert b"Anna Lopez" in body
    assert b"Family" in body or b"family" in body


@pytest.mark.django_db
def test_profile_handles_missing_address_and_caregiver(client):
    """A bare account (no address, no caregiver, no diet, no allergies)
    must still render 200 — placeholders show, the page never blows up."""
    user = UserFactory(role="member")
    client.force_login(user)
    response = client.get("/profile/")
    assert response.status_code == 200


@pytest.mark.django_db
def test_profile_has_sign_out_form(client):
    """Sign-out moves OFF the bottom nav (per 12.1) and INTO the Profile
    page. The form must POST to the logout URL — no GET-based logout."""
    user = UserFactory(role="member")
    client.force_login(user)
    response = client.get("/profile/")
    body = response.content
    assert b"Sign out" in body
    assert b'action="/accounts/logout/"' in body


@pytest.mark.django_db
def test_profile_no_dead_links(client):
    user = UserFactory(role="member")
    client.force_login(user)
    response = client.get("/profile/")
    assert b'href="#"' not in response.content
