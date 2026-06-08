import pytest
from django.core.exceptions import ValidationError

from apps.accounts.tests.factories import UserFactory
from apps.volunteers.models import Availability
from apps.volunteers.tests.factories import AvailabilityFactory, VolunteerFactory


@pytest.mark.django_db
def test_availability_persists_with_volunteer_role():
    slot = AvailabilityFactory(day_of_week="mon", day_phrase="morning")
    assert slot.pk is not None
    assert slot.volunteer.role == "volunteer"


@pytest.mark.django_db
def test_volunteer_can_have_multiple_phrases_same_day():
    vol = VolunteerFactory()
    AvailabilityFactory(volunteer=vol, day_of_week="mon", day_phrase="morning")
    AvailabilityFactory(volunteer=vol, day_of_week="mon", day_phrase="afternoon")
    assert Availability.objects.filter(volunteer=vol, day_of_week="mon").count() == 2


@pytest.mark.django_db
def test_clean_rejects_non_volunteer_user():
    member = UserFactory(role="member")
    slot = Availability(volunteer=member, day_of_week="tue", day_phrase="morning")
    with pytest.raises(ValidationError):
        slot.full_clean()


@pytest.mark.django_db
def test_db_table_name_matches_schema():
    assert Availability._meta.db_table == "volunteer_availabilities"


@pytest.mark.django_db
def test_no_unique_constraint_on_volunteer_day_phrase():
    constraints = {c.name for c in Availability._meta.constraints}
    # We intentionally allow duplicates at the DB level — toggling is row-by-row.
    assert not any(name.startswith("uq_") for name in constraints)
