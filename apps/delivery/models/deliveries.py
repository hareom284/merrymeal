from django.conf import settings
from django.db import models


class Delivery(models.Model):
    """Schema only — one (member, meal_plan, scheduled_date) tuple.

    Logic (`create_delivery`, `mark_delivered`, etc.) lives in
    `apps/delivery/services/`.
    """

    MEAL_TYPE_FRESH = "fresh"
    MEAL_TYPE_FROZEN = "frozen"
    MEAL_TYPE_CHOICES = [
        (MEAL_TYPE_FRESH, "Fresh"),
        (MEAL_TYPE_FROZEN, "Frozen"),
    ]

    STATUS_PENDING = "pending"
    STATUS_OUT_FOR_DELIVERY = "out_for_delivery"
    STATUS_DELIVERED = "delivered"
    STATUS_FAILED = "failed"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_OUT_FOR_DELIVERY, "Out for delivery"),
        (STATUS_DELIVERED, "Delivered"),
        (STATUS_FAILED, "Failed"),
    ]

    route = models.ForeignKey(
        "delivery.Route",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="deliveries",
        db_column="route_id",
    )
    meal_plan = models.ForeignKey(
        "planning.MealPlan",
        on_delete=models.PROTECT,
        related_name="deliveries",
        db_column="meal_plan_id",
    )
    volunteer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="delivered_deliveries",
        db_column="volunteer_id",
    )
    member = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="received_deliveries",
        db_column="member_id",
    )
    member_address = models.ForeignKey(
        "accounts.Address",
        on_delete=models.PROTECT,
        related_name="deliveries",
        db_column="member_address_id",
    )

    meal_type = models.CharField(
        max_length=10, choices=MEAL_TYPE_CHOICES, default=MEAL_TYPE_FRESH
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING
    )
    scheduled_date = models.DateField(null=True, blank=True)
    delivered_time = models.DateTimeField(null=True, blank=True)
    latitude = models.DecimalField(
        max_digits=10, decimal_places=7, null=True, blank=True
    )
    longitude = models.DecimalField(
        max_digits=10, decimal_places=7, null=True, blank=True
    )
    photo = models.URLField(max_length=512, null=True, blank=True)
    # Story 4.10 — when a stop transitions to ``failed``, the volunteer
    # picks one of four UI reason slugs and may add a free-text note. We
    # store the combined string here as ``slug`` or ``slug: notes`` so
    # Epic 06 reporting can group by slug while still surfacing the
    # original note to the admin follow-up screen.
    failure_reason = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "delivery"
        db_table = "deliveries"
        indexes = [
            models.Index(fields=["route"], name="idx_del_route"),
            models.Index(fields=["meal_plan"], name="idx_del_plan"),
            models.Index(fields=["member"], name="idx_del_member"),
            # For Story 4.6 idempotency (one delivery per member per date).
            models.Index(fields=["member", "scheduled_date"], name="idx_del_member_date"),
            models.Index(fields=["scheduled_date", "status"], name="idx_del_date_status"),
        ]

    def __str__(self) -> str:
        return f"Delivery #{self.pk or '?'} member={self.member_id} {self.scheduled_date}"
