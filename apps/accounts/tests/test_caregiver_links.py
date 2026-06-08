import pytest
from django.contrib import admin as django_admin
from django.db import IntegrityError

from apps.accounts.models import CaregiverLink, User
from apps.accounts.services import link_caregiver
from apps.accounts.tests.factories import UserFactory


@pytest.mark.django_db
def test_link_caregiver_creates_a_row_for_valid_roles():
    member = UserFactory(role="member")
    caregiver = UserFactory(role="caregiver")
    link = link_caregiver(member=member, caregiver=caregiver, relationship="family")
    assert link.pk is not None
    assert link.member_id == member.pk
    assert link.caregiver_id == caregiver.pk
    assert link.relationship == "family"


@pytest.mark.django_db
def test_link_caregiver_rejects_non_member_member():
    not_a_member = UserFactory(role="volunteer")
    caregiver = UserFactory(role="caregiver")
    with pytest.raises(ValueError, match="member"):
        link_caregiver(member=not_a_member, caregiver=caregiver, relationship="family")


@pytest.mark.django_db
def test_link_caregiver_rejects_non_caregiver_caregiver():
    member = UserFactory(role="member")
    not_a_caregiver = UserFactory(role="donor")
    with pytest.raises(ValueError, match="caregiver"):
        link_caregiver(member=member, caregiver=not_a_caregiver, relationship="family")


@pytest.mark.django_db
def test_caregiver_link_db_table_is_member_caregivers():
    assert CaregiverLink._meta.db_table == "member_caregivers"


@pytest.mark.django_db
def test_relationship_choices_match_schema():
    field = CaregiverLink._meta.get_field("relationship")
    values = {c[0] for c in field.choices}
    assert values == {"family", "friend", "nurse", "social_worker", "other"}


@pytest.mark.django_db
def test_uniqueness_member_caregiver_pair():
    member = UserFactory(role="member")
    caregiver = UserFactory(role="caregiver")
    link_caregiver(member=member, caregiver=caregiver, relationship="family")
    with pytest.raises(IntegrityError):
        CaregiverLink.objects.create(
            member=member, caregiver=caregiver, relationship="friend"
        )


@pytest.mark.django_db
def test_same_caregiver_can_link_to_multiple_members():
    caregiver = UserFactory(role="caregiver")
    margaret = UserFactory(role="member", email="margaret@example.com")
    edith = UserFactory(role="member", email="edith@example.com")
    link_caregiver(member=margaret, caregiver=caregiver, relationship="family")
    link_caregiver(member=edith, caregiver=caregiver, relationship="nurse")
    assert CaregiverLink.objects.filter(caregiver=caregiver).count() == 2


def test_two_caregiver_link_inlines_registered_on_user_admin():
    user_admin = django_admin.site._registry[User]
    inline_models = [inline.model for inline in user_admin.inlines]
    assert inline_models.count(CaregiverLink) == 2


def test_caregiver_link_inlines_use_fk_name_to_disambiguate():
    user_admin = django_admin.site._registry[User]
    cl_inlines = [
        inline for inline in user_admin.inlines if inline.model is CaregiverLink
    ]
    fk_names = {inline.fk_name for inline in cl_inlines}
    assert fk_names == {"member", "caregiver"}
