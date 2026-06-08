import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from apps.delivery.models import DeliveryFeedback
from apps.delivery.tests.factories import DeliveryFactory, DeliveryFeedbackFactory


@pytest.mark.django_db
def test_feedback_persists():
    fb = DeliveryFeedbackFactory(rating=4, note="Tasty.")
    assert fb.pk is not None
    assert fb.rating == 4
    assert fb.note == "Tasty."


@pytest.mark.django_db
def test_db_table_matches_schema():
    assert DeliveryFeedback._meta.db_table == "delivery_feedback"


@pytest.mark.django_db
def test_one_to_one_with_delivery():
    fb = DeliveryFeedbackFactory()
    # Reverse access works.
    assert fb.delivery.feedback == fb


@pytest.mark.django_db
def test_second_feedback_for_same_delivery_raises_integrity_error():
    delivery = DeliveryFactory()
    DeliveryFeedbackFactory(delivery=delivery, rating=5)
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            DeliveryFeedbackFactory(delivery=delivery, rating=3)


@pytest.mark.django_db
def test_rating_validators_reject_out_of_range():
    fb = DeliveryFeedbackFactory.build(rating=0)
    with pytest.raises(ValidationError):
        fb.full_clean()

    fb_high = DeliveryFeedbackFactory.build(rating=6)
    with pytest.raises(ValidationError):
        fb_high.full_clean()


@pytest.mark.django_db
def test_rating_can_be_null_per_schema():
    fb = DeliveryFeedbackFactory(rating=None, note="No rating but a note")
    fb.refresh_from_db()
    assert fb.rating is None
    assert fb.note == "No rating but a note"


@pytest.mark.django_db
def test_note_can_be_empty():
    fb = DeliveryFeedbackFactory(rating=5, note="")
    assert fb.note == ""
