from django.db import models

from apps.core.models import SoftDeleteModel


class City(SoftDeleteModel):
    name = models.CharField(max_length=120)

    class Meta:
        app_label = "accounts"
        db_table = "cities"
        ordering = ("name",)

    def __str__(self) -> str:
        return self.name
