import pytest

from apps.accounts.tests.factories import UserFactory


@pytest.mark.django_db
def test_landing_page_renders_for_anonymous_visitor(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"Apply for meals" in response.content


@pytest.mark.django_db
def test_landing_page_has_three_persona_cards(client):
    response = client.get("/")
    body = response.content
    assert b"For members" in body
    assert b"For caregivers" in body
    assert b"For volunteers" in body


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
def test_landing_title_includes_brand_and_tagline(client):
    response = client.get("/")
    assert b"MerryMeal" in response.content
    assert b"Warm meals, delivered with care" in response.content


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
