import pytest

from apps.accounts.tests.factories import UserFactory


@pytest.mark.django_db
def test_landing_page_renders_for_anonymous_visitor(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"Apply for meals" in response.content


@pytest.mark.django_db
def test_landing_page_lists_every_get_involved_path(client):
    """The landing page is the 'How would you like to help?' role
    picker. Each of the four entry-points must be present so the user
    can self-serve into the right flow without having to ask."""
    response = client.get("/")
    body = response.content
    assert b"Apply for meals" in body
    assert b"caregiver" in body
    assert b"Become a volunteer" in body
    assert b"Partner with us" in body


@pytest.mark.django_db
def test_landing_cta_points_to_apply(client):
    response = client.get("/")
    assert b'href="/apply/"' in response.content


@pytest.mark.django_db
def test_caregiver_card_passes_for_other_flag(client):
    response = client.get("/")
    assert b'href="/apply/?for_other=1"' in response.content


@pytest.mark.django_db
def test_volunteer_card_uses_mailto_link(client):
    response = client.get("/")
    assert b"mailto:hello@merrymeal.org.au" in response.content


@pytest.mark.django_db
def test_landing_title_includes_brand_and_new_headline(client):
    """Story 12.2 — landing copy shifted from a role-picker
    (\"How would you like to help?\") to a member-first marketing
    headline. The new design leads with the value prop, then offers
    Apply for meals + Donate as primary actions."""
    response = client.get("/")
    body = response.content
    assert b"MerryMeal" in body
    assert b"friendly smile" in body
    assert b"5,000+ MEALS DAILY" in body


@pytest.mark.django_db
def test_landing_has_how_it_works_section(client):
    response = client.get("/")
    body = response.content
    assert b"How it works" in body or b"HOW IT WORKS" in body
    assert b"Three caring steps" in body
    assert b"01" in body


@pytest.mark.django_db
def test_landing_donate_cta_present(client):
    """Donate is now a top-level CTA on landing, not a tiny footer link."""
    response = client.get("/")
    body = response.content
    assert b"Donate" in body
    assert b"/donate/" in body


@pytest.mark.django_db
def test_authenticated_user_at_root_is_redirected_to_dashboard(client):
    user = UserFactory(role="member")
    client.force_login(user)
    response = client.get("/")
    assert response.status_code == 302
    assert response.url == "/dashboard/"


@pytest.mark.django_db
def test_member_dashboard_now_lives_at_slash_dashboard(client):
    user = UserFactory(role="member")
    client.force_login(user)
    response = client.get("/dashboard/")
    assert response.status_code == 200
    assert b"Today's delivery" in response.content
