from django.db import models


class DietPreference(models.Model):
    """Controlled list of diet preferences (vegan, halal, …).

    Schema only — see merrymeal_schema_corrected.sql::diet_preferences.
    """

    name = models.CharField(max_length=80, unique=True)

    class Meta:
        app_label = "dietary"
        db_table = "diet_preferences"
        ordering = ("name",)

    def __str__(self) -> str:
        return self.name


class UserDietPreference(models.Model):
    """Through-table: which users declared which preferences.

    DB schema uses a composite PK (user_id, diet_preference_id) with no
    surrogate `id`. Django 5.1 still requires a single-column PK, so we
    let Django add an auto `id` and enforce the pair-uniqueness via
    UniqueConstraint. Downstream code reads/writes via the FKs, never `id`.
    """

    user = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="diet_preference_links",
        db_column="user_id",
    )
    diet_preference = models.ForeignKey(
        "dietary.DietPreference",
        on_delete=models.PROTECT,
        related_name="user_links",
        db_column="diet_preference_id",
    )

    class Meta:
        app_label = "dietary"
        db_table = "diet_preference_user"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "diet_preference"],
                name="uq_user_diet_preference",
            ),
        ]

    def __str__(self) -> str:
        return f"User {self.user_id} → {self.diet_preference_id}"
