import pytest
from django.core.exceptions import ValidationError

from apps.accounts.tests.factories import UserFactory
from apps.volunteers.models import Availability
from apps.volunteers.services.availability import toggle_slot
from apps.volunteers.tests.factories import VolunteerFactory


@pytest.mark.django_db
def test_toggle_creates_when_absent():
    vol = VolunteerFactory()
    created = toggle_slot(vol, "mon", "morning")
    assert created is True
    assert Availability.objects.filter(
        volunteer=vol, day_of_week="mon", day_phrase="morning"
    ).exists()


@pytest.mark.django_db
def test_toggle_removes_when_present():
    vol = VolunteerFactory()
    toggle_slot(vol, "mon", "morning")
    removed_state = toggle_slot(vol, "mon", "morning")
    assert removed_state is False
    assert not Availability.objects.filter(
        volunteer=vol, day_of_week="mon", day_phrase="morning"
    ).exists()


@pytest.mark.django_db
def test_toggle_independent_phrases_same_day():
    vol = VolunteerFactory()
    toggle_slot(vol, "mon", "morning")
    toggle_slot(vol, "mon", "afternoon")
    assert Availability.objects.filter(volunteer=vol, day_of_week="mon").count() == 2


@pytest.mark.django_db
def test_toggle_rejects_invalid_day():
    vol = VolunteerFactory()
    with pytest.raises(ValueError):
        toggle_slot(vol, "funday", "morning")


@pytest.mark.django_db
def test_toggle_rejects_invalid_phrase():
    vol = VolunteerFactory()
    with pytest.raises(ValueError):
        toggle_slot(vol, "mon", "midnight")


@pytest.mark.django_db
def test_toggle_rejects_non_volunteer():
    member = UserFactory(role="member")
    with pytest.raises(ValidationError):
        toggle_slot(member, "mon", "morning")
