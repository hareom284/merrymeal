from django.db import models
from django.utils import timezone


def soft_delete(instance: models.Model) -> None:
    """Set deleted_at to now and save. Works for any model that has a
    `deleted_at` field (typically subclasses of SoftDeleteModel).
    """
    if not hasattr(instance, "deleted_at"):
        raise TypeError(
            f"{type(instance).__name__} has no `deleted_at` field — "
            "cannot soft delete. Subclass SoftDeleteModel or use .delete()."
        )
    instance.deleted_at = timezone.now()
    instance.save(update_fields=["deleted_at", "updated_at"])
