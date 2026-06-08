from django.conf import settings
from django.db import models


class Route(models.Model):
    """Schema only — one volunteer's deliveries on one day.

    Status transitions and packing logic live in
    `apps/delivery/services/dispatch.py` (Story 4.7).
    """

    STATUS_PLANNED = "planned"
    STATUS_IN_PROGRESS = "in_progress"
    STATUS_COMPLETED = "completed"
    STATUS_CANCELLED = "cancelled"

    STATUS_CHOICES = [
        (STATUS_PLANNED, "Planned"),
        (STATUS_IN_PROGRESS, "In progress"),
        (STATUS_COMPLETED, "Completed"),
        (STATUS_CANCELLED, "Cancelled"),
    ]

    volunteer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="routes",
        db_column="volunteer_id",
    )
    route_date = models.DateField()
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_PLANNED
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "delivery"
        db_table = "routes"
        indexes = [
            models.Index(fields=["volunteer"], name="idx_route_volunteer"),
            models.Index(fields=["volunteer", "route_date"], name="idx_route_vol_date"),
            models.Index(fields=["route_date"], name="idx_route_date"),
        ]

    def __str__(self) -> str:
        return f"Route #{self.pk or '?'} {self.route_date} vol={self.volunteer_id}"
