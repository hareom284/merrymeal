from django.db import models

from apps.core.managers import AllObjectsManager, SoftDeleteManager

from .timestamped import TimeStampedModel


class SoftDeleteModel(TimeStampedModel):
    """Schema-only: adds a `deleted_at` column and managers that
    filter it out by default. The soft-delete *operation* lives in
    apps.core.services.soft_delete — do not override delete() here.
    """

    deleted_at = models.DateTimeField(null=True, blank=True)

    objects = SoftDeleteManager()
    all_objects = AllObjectsManager()

    class Meta:
        abstract = True
