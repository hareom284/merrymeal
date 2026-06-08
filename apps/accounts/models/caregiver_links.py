from django.db import models


class CaregiverLink(models.Model):
    """Links a member User to a caregiver User. M2M-through.

    Schema-only. Role validation lives in
    `apps.accounts.services.caregiver_links.link_caregiver`.
    """

    RELATIONSHIP_CHOICES = [
        ("family", "Family"),
        ("friend", "Friend"),
        ("nurse", "Nurse"),
        ("social_worker", "Social worker"),
        ("other", "Other"),
    ]

    member = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="caregiver_links_as_member",
        db_column="member_id",
    )
    caregiver = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="caregiver_links_as_caregiver",
        db_column="caregiver_id",
    )
    relationship = models.CharField(max_length=20, choices=RELATIONSHIP_CHOICES)

    class Meta:
        app_label = "accounts"
        db_table = "member_caregivers"
        constraints = [
            models.UniqueConstraint(
                fields=["member", "caregiver"],
                name="uq_member_caregiver",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.member_id} ← {self.caregiver_id} ({self.relationship})"
