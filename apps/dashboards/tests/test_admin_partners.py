"""Tests for the admin partners CRU (Story 12.15)."""
import pytest

from apps.accounts.models import Application
from apps.accounts.tests.factories import UserFactory
from apps.partners.models import Partner


@pytest.mark.django_db
def test_partners_list_requires_admin(client):
    user = UserFactory(role="member")
    client.force_login(user)
    response = client.get("/admin/partners/")
    assert response.status_code == 403


@pytest.mark.django_db
def test_partners_list_renders_with_seed_partners(client):
    admin = UserFactory(role="admin")
    Partner.objects.create(legal_name="Sunset Charity", type="charity")
    Partner.objects.create(legal_name="Bistro Roma", type="restaurant")
    client.force_login(admin)
    response = client.get("/admin/partners/")
    assert response.status_code == 200
    body = response.content
    assert b"Sunset Charity" in body
    assert b"Bistro Roma" in body


@pytest.mark.django_db
def test_partners_list_search_by_legal_name(client):
    admin = UserFactory(role="admin")
    Partner.objects.create(legal_name="Sunset Charity", type="charity")
    p2 = Partner.objects.create(legal_name="Bistro Roma", type="restaurant")
    client.force_login(admin)
    response = client.get("/admin/partners/", {"q": "Sunset"})
    body = response.content
    assert b"Sunset Charity" in body
    # Use detail-link URL to assert exclusion (the legal name might also
    # appear in a filter dropdown or other chrome).
    assert f"/admin/partners/{p2.id}/".encode() not in body


@pytest.mark.django_db
def test_partners_list_filter_by_type(client):
    admin = UserFactory(role="admin")
    p_charity = Partner.objects.create(legal_name="A Charity", type="charity")
    p_restaurant = Partner.objects.create(legal_name="A Restaurant", type="restaurant")
    client.force_login(admin)
    response = client.get("/admin/partners/", {"type": "charity"})
    body = response.content
    assert f"/admin/partners/{p_charity.id}/".encode() in body
    assert f"/admin/partners/{p_restaurant.id}/".encode() not in body


@pytest.mark.django_db
def test_partner_detail_shows_affiliated_members(client):
    admin = UserFactory(role="admin")
    partner = Partner.objects.create(legal_name="Hope Charity", type="charity")
    m = UserFactory(
        role="member", full_name="Margaret Member", partner=partner
    )
    client.force_login(admin)
    response = client.get(f"/admin/partners/{partner.id}/")
    body = response.content
    assert response.status_code == 200
    assert b"Margaret Member" in body
    # Detail link to the member must be there so admin can drill through.
    assert f"/admin/members/{m.id}/".encode() in body


@pytest.mark.django_db
def test_partner_detail_shows_referrals(client):
    """Applications submitted via the partner referral form (with the
    partner FK set) must surface in the partner's detail page so admins
    can see what came through which channel."""
    from datetime import date

    admin = UserFactory(role="admin")
    partner = Partner.objects.create(legal_name="Hope Charity", type="charity")
    Application.objects.create(
        full_name="Referred Person",
        email="r@example.com",
        dob=date(1950, 1, 1),
        status=Application.STATUS_SUBMITTED,
        partner=partner,
    )
    client.force_login(admin)
    response = client.get(f"/admin/partners/{partner.id}/")
    assert b"Referred Person" in response.content
    # Referral count badge should reflect the row.
    assert b"1 referral" in response.content


@pytest.mark.django_db
def test_partner_detail_404_for_unknown(client):
    admin = UserFactory(role="admin")
    client.force_login(admin)
    response = client.get("/admin/partners/9999999/")
    assert response.status_code == 404


@pytest.mark.django_db
def test_partner_create_post_persists_and_redirects(client):
    admin = UserFactory(role="admin")
    client.force_login(admin)
    response = client.post("/admin/partners/new/", {
        "legal_name": "Brand New Charity",
        "type": "charity",
    })
    assert response.status_code == 302
    partner = Partner.objects.get(legal_name="Brand New Charity")
    assert partner.type == "charity"
    assert response.url == f"/admin/partners/{partner.id}/"


@pytest.mark.django_db
def test_partner_create_get_renders_form(client):
    admin = UserFactory(role="admin")
    client.force_login(admin)
    response = client.get("/admin/partners/new/")
    assert response.status_code == 200
    assert b"Add partner" in response.content


@pytest.mark.django_db
def test_partner_edit_updates_name(client):
    admin = UserFactory(role="admin")
    partner = Partner.objects.create(legal_name="Old Name", type="charity")
    client.force_login(admin)
    response = client.post(f"/admin/partners/{partner.id}/edit/", {
        "legal_name": "New Name",
        "type": "charity",
    })
    assert response.status_code == 302
    partner.refresh_from_db()
    assert partner.legal_name == "New Name"


@pytest.mark.django_db
def test_admin_home_links_to_partners(client):
    admin = UserFactory(role="admin")
    client.force_login(admin)
    response = client.get("/admin/home/")
    assert b"/admin/partners/" in response.content


@pytest.mark.django_db
def test_admin_partners_has_no_delete_route():
    """Design contract: Partner is PROTECTed by Application.partner and
    User.partner. A hard delete fails if any data refers to it, so we
    don't expose a delete URL. Same reasoning as Kitchens."""
    from django.urls import NoReverseMatch, reverse

    with pytest.raises(NoReverseMatch):
        reverse("dashboards:admin_partner_delete")
