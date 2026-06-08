from django.db import models


class ExpiryAlertLog(models.Model):
    """One row per (kitchen, sent_date). Makes the daily expiry-alert task
    idempotent within a calendar day."""

    kitchen = models.ForeignKey(
        "kitchens.Kitchen",
        on_delete=models.CASCADE,
        db_column="kitchen_id",
        related_name="expiry_alert_logs",
    )
    sent_date = models.DateField()
    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "expiry_alert_logs"
        constraints = [
            models.UniqueConstraint(
                fields=["kitchen", "sent_date"],
                name="uniq_alert_kitchen_day",
            ),
        ]

    def __str__(self) -> str:
        return f"alert log {self.kitchen_id} {self.sent_date}"
