from django.db import models

from apps.core.models import TimeStampedModel


class Partner(TimeStampedModel):
    """Referring organisations: charities, restaurants, suppliers, corporates.

    Schema only — see merrymeal_schema_corrected.sql::partners.
    """

    TYPE_CHOICES = [
        ("charity", "Charity"),
        ("restaurant", "Restaurant"),
        ("supplier", "Supplier"),
        ("corporate", "Corporate"),
    ]

    legal_name = models.CharField(max_length=255)
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)

    class Meta:
        app_label = "partners"
        db_table = "partners"
        ordering = ("legal_name",)

    def __str__(self) -> str:
        return self.legal_name
