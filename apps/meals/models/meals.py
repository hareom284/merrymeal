from django.db import models

from apps.core.models.soft_delete import SoftDeleteModel


class Meal(SoftDeleteModel):
    name = models.CharField(max_length=160)
    description = models.TextField(null=True, blank=True)
    prep_time_minutes = models.PositiveIntegerField(null=True, blank=True)
    cook_time_minutes = models.PositiveIntegerField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        app_label = "meals"
        db_table = "meals"

    def __str__(self) -> str:
        return self.name
