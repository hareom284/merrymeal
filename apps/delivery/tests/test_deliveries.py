from decimal import Decimal
from unittest.mock import patch

import pytest

from apps.accounts.tests.factories import UserFactory
from apps.delivery.models import Delivery
from apps.delivery.services.deliveries import create_delivery
from apps.delivery.tests.factories import DeliveryFactory


@pytest.mark.django_db
def test_delivery_persists_with_factory_defaults():
    d = DeliveryFactory()
    assert d.pk is not None
    assert d.status == "pending"
    assert d.route is None  # nullable, packed later by 4.7


@pytest.mark.django_db
def test_db_table_matches_schema():
    assert Delivery._meta.db_table == "deliveries"


@pytest.mark.django_db
def test_status_choices_match_schema():
    assert {c for c, _ in Delivery.STATUS_CHOICES} == {
        "pending", "out_for_delivery", "delivered", "failed"
    }


@pytest.mark.django_db
def test_meal_type_choices_match_schema():
    assert {c for c, _ in Delivery.MEAL_TYPE_CHOICES} == {"fresh", "frozen"}


@pytest.mark.django_db
@patch("apps.delivery.services.deliveries.assign_meal_type", return_value="fresh")
def test_create_delivery_calls_assign_meal_type_with_kitchen(mock_assign):
    d = DeliveryFactory()
    # Use the factory pieces but route through the service:
    delivery = create_delivery(
        member=d.member,
        member_address=d.member_address,
        meal_plan=d.meal_plan,
        volunteer=d.volunteer,
        scheduled_date=d.scheduled_date,
    )
    mock_assign.assert_called_once_with(
        member=d.member,
        kitchen=d.meal_plan.kitchen,
        scheduled_date=d.scheduled_date,
    )
    assert delivery.meal_type == "fresh"


@pytest.mark.django_db
@patch("apps.delivery.services.deliveries.assign_meal_type", return_value="frozen")
def test_create_delivery_uses_returned_meal_type(mock_assign):
    d = DeliveryFactory()
    delivery = create_delivery(
        member=d.member,
        member_address=d.member_address,
        meal_plan=d.meal_plan,
        volunteer=d.volunteer,
        scheduled_date=d.scheduled_date,
    )
    assert delivery.meal_type == "frozen"


@pytest.mark.django_db
def test_create_delivery_rejects_non_member():
    not_a_member = UserFactory(role="volunteer")
    d = DeliveryFactory()
    with pytest.raises(ValueError):
        create_delivery(
            member=not_a_member,
            member_address=d.member_address,
            meal_plan=d.meal_plan,
            volunteer=d.volunteer,
            scheduled_date=d.scheduled_date,
        )


@pytest.mark.django_db
def test_decimal_fields_round_trip_seven_places():
    d = DeliveryFactory(
        latitude=Decimal("-37.8136123"),
        longitude=Decimal("144.9630985"),
    )
    d.refresh_from_db()
    assert d.latitude == Decimal("-37.8136123")
    assert d.longitude == Decimal("144.9630985")
