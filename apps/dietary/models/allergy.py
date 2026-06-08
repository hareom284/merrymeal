from django.db import models


class Allergy(models.Model):
    """Controlled list of allergies.

    Schema only — see merrymeal_schema_corrected.sql::allergies.
    """

    name = models.CharField(max_length=80, unique=True)

    class Meta:
        app_label = "dietary"
        db_table = "allergies"
        ordering = ("name",)

    def __str__(self) -> str:
        return self.name


class UserAllergy(models.Model):
    """Through-table: which users declared which allergies.

    See UserDietPreference for the composite-PK / surrogate-id note.
    """

    user = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="allergy_links",
        db_column="user_id",
    )
    allergy = models.ForeignKey(
        "dietary.Allergy",
        on_delete=models.PROTECT,
        related_name="user_links",
        db_column="allergy_id",
    )

    class Meta:
        app_label = "dietary"
        db_table = "allergy_user"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "allergy"],
                name="uq_user_allergy",
            ),
        ]

    def __str__(self) -> str:
        return f"User {self.user_id} → {self.allergy_id}"
