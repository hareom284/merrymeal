from django.db import models

from apps.core.models import TimeStampedModel


class Address(TimeStampedModel):
    """A delivery address. One user can have many.

    Schema only — see merrymeal_schema_corrected.sql::user_addresses.
    Lat/lng are nullable; geocoding lands in Story 1.10.
    """

    user = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="addresses",
        db_column="user_id",
    )
    label = models.CharField(max_length=120, null=True, blank=True)
    postal_code = models.CharField(max_length=20, null=True, blank=True)
    city = models.ForeignKey(
        "accounts.City",
        on_delete=models.PROTECT,
        related_name="addresses",
        db_column="city_id",
    )
    latitude = models.DecimalField(
        max_digits=10, decimal_places=7, null=True, blank=True
    )
    longitude = models.DecimalField(
        max_digits=10, decimal_places=7, null=True, blank=True
    )

    class Meta:
        app_label = "accounts"
        db_table = "user_addresses"
        indexes = [
            models.Index(fields=["user"], name="idx_addr_user"),
            models.Index(fields=["city"], name="idx_addr_city"),
        ]

    def __str__(self) -> str:
        return f"{self.label or 'Address'} ({self.postal_code or '—'})"
