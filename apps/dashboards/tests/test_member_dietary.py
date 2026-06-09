"""Member-facing dietary edit page.

Lets a member update their `diet_preferences` and `allergies` M2Ms from
the profile. Strict role gate (member-only) — caregivers / volunteers /
admins cannot reach this view; admins have their own member-detail
screens for the same data.
"""
import re

import pytest
from django.urls import reverse

from apps.accounts.tests.factories import UserFactory
from apps.dietary.models import (
    Allergy,
    DietPreference,
    UserAllergy,
    UserDietPreference,
)


def _is_checkbox_checked(body: str, pk: int) -> bool:
    """True iff a single ``<input>`` tag with both ``value="<pk>"`` and
    the ``checked`` attribute exists in ``body``. Tolerates any attribute
    order Django picks (``value`` and ``checked`` are often separated
    by an auto-generated ``id``)."""
    pattern = rf'<input[^>]*\bvalue="{pk}"[^>]*\bchecked\b[^>]*>'
    if re.search(pattern, body):
        return True
    pattern_rev = rf'<input[^>]*\bchecked\b[^>]*\bvalue="{pk}"[^>]*>'
    return bool(re.search(pattern_rev, body))


URL_NAME = "dashboards:member_dietary_edit"


@pytest.fixture
def diet_prefs(db):
    return {
        "vegan": DietPreference.objects.create(name="vegan"),
        "halal": DietPreference.objects.create(name="halal"),
        "gluten-free": DietPreference.objects.create(name="gluten-free"),
    }


@pytest.fixture
def allergies(db):
    return {
        "peanut": Allergy.objects.create(name="peanut"),
        "dairy": Allergy.objects.create(name="dairy"),
        "egg": Allergy.objects.create(name="egg"),
    }


@pytest.mark.django_db
def test_anonymous_redirected_to_login(client):
    resp = client.get(reverse(URL_NAME))
    assert resp.status_code == 302
    assert "/accounts/login" in resp.url or "/login" in resp.url


@pytest.mark.django_db
def test_non_member_forbidden(client):
    volunteer = UserFactory(role="volunteer")
    client.force_login(volunteer)
    resp = client.get(reverse(URL_NAME))
    assert resp.status_code == 403


@pytest.mark.django_db
def test_get_renders_form_with_current_selections_checked(
    client, diet_prefs, allergies
):
    member = UserFactory(role="member")
    UserDietPreference.objects.create(
        user=member, diet_preference=diet_prefs["vegan"]
    )
    UserAllergy.objects.create(user=member, allergy=allergies["peanut"])
    client.force_login(member)

    resp = client.get(reverse(URL_NAME))

    assert resp.status_code == 200
    body = resp.content.decode()
    assert "vegan" in body
    assert "peanut" in body
    assert _is_checkbox_checked(body, diet_prefs["vegan"].pk)
    assert _is_checkbox_checked(body, allergies["peanut"].pk)
    assert not _is_checkbox_checked(body, diet_prefs["halal"].pk)
    assert not _is_checkbox_checked(body, allergies["dairy"].pk)


@pytest.mark.django_db
def test_post_replaces_diet_preferences(client, diet_prefs, allergies):
    member = UserFactory(role="member")
    UserDietPreference.objects.create(
        user=member, diet_preference=diet_prefs["vegan"]
    )
    client.force_login(member)

    resp = client.post(
        reverse(URL_NAME),
        {
            "diet_preferences": [
                diet_prefs["halal"].pk,
                diet_prefs["gluten-free"].pk,
            ],
            "allergies": [],
        },
    )

    assert resp.status_code == 302
    assert set(
        member.diet_preferences.values_list("name", flat=True)
    ) == {"halal", "gluten-free"}


@pytest.mark.django_db
def test_post_replaces_allergies(client, diet_prefs, allergies):
    member = UserFactory(role="member")
    UserAllergy.objects.create(user=member, allergy=allergies["peanut"])
    client.force_login(member)

    resp = client.post(
        reverse(URL_NAME),
        {
            "diet_preferences": [],
            "allergies": [
                allergies["dairy"].pk,
                allergies["egg"].pk,
            ],
        },
    )

    assert resp.status_code == 302
    assert set(member.allergies.values_list("name", flat=True)) == {
        "dairy",
        "egg",
    }


@pytest.mark.django_db
def test_post_with_empty_selection_clears_both(client, diet_prefs, allergies):
    member = UserFactory(role="member")
    UserDietPreference.objects.create(
        user=member, diet_preference=diet_prefs["vegan"]
    )
    UserAllergy.objects.create(user=member, allergy=allergies["peanut"])
    client.force_login(member)

    resp = client.post(
        reverse(URL_NAME),
        {"diet_preferences": [], "allergies": []},
    )

    assert resp.status_code == 302
    assert member.diet_preferences.count() == 0
    assert member.allergies.count() == 0


@pytest.mark.django_db
def test_post_redirects_to_profile(client, diet_prefs):
    member = UserFactory(role="member")
    client.force_login(member)

    resp = client.post(
        reverse(URL_NAME),
        {"diet_preferences": [diet_prefs["vegan"].pk], "allergies": []},
    )

    assert resp.status_code == 302
    assert resp.url == reverse("dashboards:member_profile")


@pytest.mark.django_db
def test_post_only_affects_current_user(client, diet_prefs, allergies):
    me = UserFactory(role="member", email="me@x.test")
    other = UserFactory(role="member", email="other@x.test")
    UserDietPreference.objects.create(
        user=other, diet_preference=diet_prefs["vegan"]
    )
    UserAllergy.objects.create(user=other, allergy=allergies["peanut"])
    client.force_login(me)

    client.post(
        reverse(URL_NAME),
        {
            "diet_preferences": [diet_prefs["halal"].pk],
            "allergies": [allergies["dairy"].pk],
        },
    )

    assert set(other.diet_preferences.values_list("name", flat=True)) == {"vegan"}
    assert set(other.allergies.values_list("name", flat=True)) == {"peanut"}
    assert set(me.diet_preferences.values_list("name", flat=True)) == {"halal"}
    assert set(me.allergies.values_list("name", flat=True)) == {"dairy"}


@pytest.mark.django_db
def test_profile_links_to_dietary_edit_page(client):
    """The read-only profile must surface an entry-point to the editor."""
    member = UserFactory(role="member")
    client.force_login(member)

    resp = client.get(reverse("dashboards:member_profile"))

    assert resp.status_code == 200
    assert reverse(URL_NAME).encode() in resp.content
