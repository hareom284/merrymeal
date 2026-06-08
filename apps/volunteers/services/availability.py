from django.contrib.auth import get_user_model
from django.db import transaction

from apps.volunteers.models import Availability

User = get_user_model()

_VALID_DAYS = {d for d, _ in Availability.DAY_OF_WEEK_CHOICES}
_VALID_PHRASES = {p for p, _ in Availability.DAY_PHRASE_CHOICES}


def toggle_slot(volunteer, day: str, phrase: str) -> bool:
    """Add the slot if missing, remove it if present.

    Returns ``True`` if the slot is now active, ``False`` if it was just removed.

    Raises:
        ValueError: if ``day`` or ``phrase`` is not a valid choice.
        django.core.exceptions.ValidationError: if ``volunteer.role != "volunteer"``
            (re-raised from ``Availability.clean()``).
    """
    if day not in _VALID_DAYS:
        raise ValueError(f"Invalid day_of_week: {day!r}")
    if phrase not in _VALID_PHRASES:
        raise ValueError(f"Invalid day_phrase: {phrase!r}")

    with transaction.atomic():
        existing = Availability.objects.filter(
            volunteer=volunteer, day_of_week=day, day_phrase=phrase
        ).first()
        if existing:
            existing.delete()
            return False

        slot = Availability(volunteer=volunteer, day_of_week=day, day_phrase=phrase)
        slot.full_clean()  # fires role check from Story 4.1
        slot.save()
        return True
