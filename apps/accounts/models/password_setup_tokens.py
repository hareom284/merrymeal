from django.conf import settings
from django.db import models


class PasswordSetupToken(models.Model):
    """Single-use, time-bounded token for the post-approval password-set flow.

    The signed token string itself is mailed to the user. We store only a
    SHA-256 hash here so that a database leak does not leak live tokens.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="password_setup_tokens",
        db_column="user_id",
    )
    token_hash = models.CharField(max_length=64)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "accounts"
        db_table = "password_setup_tokens"
        indexes = [
            models.Index(fields=["user", "used_at"]),
            models.Index(fields=["token_hash"]),
        ]

    def __str__(self) -> str:
        return f"PasswordSetupToken<user={self.user_id} used={self.used_at is not None}>"
