from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class Availability(models.Model):
    """Schema only — one row per (volunteer, day_of_week, day_phrase) slot.

    No ``UniqueConstraint``: the editor in Story 4.2 toggles single slots in/out,
    and a volunteer may be available for ``mon morning`` AND ``mon afternoon``.
    Logic (``toggle_slot``) lives in ``apps/volunteers/services/``.
    """

    DAY_OF_WEEK_CHOICES = [
        ("mon", "Monday"),
        ("tue", "Tuesday"),
        ("wed", "Wednesday"),
        ("thu", "Thursday"),
        ("fri", "Friday"),
        ("sat", "Saturday"),
        ("sun", "Sunday"),
    ]

    DAY_PHRASE_CHOICES = [
        ("morning", "Morning"),
        ("afternoon", "Afternoon"),
        ("evening", "Evening"),
    ]

    volunteer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="availabilities",
        db_column="volunteer_id",
    )
    day_of_week = models.CharField(max_length=3, choices=DAY_OF_WEEK_CHOICES)
    day_phrase = models.CharField(max_length=10, choices=DAY_PHRASE_CHOICES)

    class Meta:
        app_label = "volunteers"
        db_table = "volunteer_availabilities"
        indexes = [
            models.Index(fields=["volunteer"], name="idx_avail_volunteer"),
        ]

    def __str__(self) -> str:
        return f"{self.volunteer_id}:{self.day_of_week}:{self.day_phrase}"

    def clean(self):
        if self.volunteer_id and self.volunteer.role != "volunteer":
            raise ValidationError(
                {"volunteer": "Only users with role='volunteer' may have availability."}
            )
