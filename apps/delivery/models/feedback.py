from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class DeliveryFeedback(models.Model):
    """Schema only — exactly one feedback row per delivery.

    The form layer (Story 4.11) shapes how rating/note are captured;
    this file is just the table.
    """

    delivery = models.OneToOneField(
        "delivery.Delivery",
        on_delete=models.CASCADE,
        related_name="feedback",
        db_column="delivery_id",
    )
    rating = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
    )
    note = models.TextField(null=True, blank=True)

    class Meta:
        app_label = "delivery"
        db_table = "delivery_feedback"
        constraints = [
            models.UniqueConstraint(
                fields=["delivery"], name="uq_feedback_delivery"
            ),
        ]

    def __str__(self) -> str:
        return f"Feedback(delivery={self.delivery_id}, rating={self.rating})"
