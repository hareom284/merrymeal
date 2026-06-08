from decimal import Decimal

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from apps.core.models.timestamped import TimeStampedModel


class Kitchen(TimeStampedModel):
    name = models.CharField(max_length=160)
    partner_id = models.BigIntegerField(null=True, blank=True)
    is_outsourced = models.BooleanField(default=False)
    latitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        validators=[MinValueValidator(Decimal("-90")), MaxValueValidator(Decimal("90"))],
    )
    longitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        validators=[MinValueValidator(Decimal("-180")), MaxValueValidator(Decimal("180"))],
    )
    service_radius_km = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("10.00"),
    )

    class Meta:
        app_label = "kitchens"
        db_table = "kitchens"
        indexes = [models.Index(fields=["partner_id"])]

    def __str__(self) -> str:
        return self.name
