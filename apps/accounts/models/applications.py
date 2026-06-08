from django.db import models


class Application(models.Model):
    STATUS_DRAFT = "draft"
    STATUS_SUBMITTED = "submitted"
    STATUS_APPROVED = "approved"
    STATUS_REJECTED = "rejected"
    STATUS_CHOICES = [
        (STATUS_DRAFT, "Draft"),
        (STATUS_SUBMITTED, "Submitted"),
        (STATUS_APPROVED, "Approved"),
        (STATUS_REJECTED, "Rejected"),
    ]

    RELATIONSHIP_CHOICES = [
        ("family", "Family"),
        ("friend", "Friend"),
        ("nurse", "Nurse"),
        ("social_worker", "Social worker"),
        ("other", "Other"),
    ]

    # ---- step 1: applicant contact ----
    full_name = models.CharField(max_length=255)
    email = models.EmailField(max_length=255)
    dob = models.DateField()
    phone = models.CharField(max_length=32, null=True, blank=True)

    # ---- step 1 (Story 1.10): caregiver-on-behalf toggle ----
    applying_for_other = models.BooleanField(default=False)
    caregiver_full_name = models.CharField(max_length=255, null=True, blank=True)
    caregiver_email = models.EmailField(max_length=255, null=True, blank=True)
    caregiver_phone = models.CharField(max_length=32, null=True, blank=True)
    relationship = models.CharField(
        max_length=20, choices=RELATIONSHIP_CHOICES, null=True, blank=True
    )

    # ---- step 2 (Story 1.8): address ----
    address_label = models.CharField(max_length=120, null=True, blank=True)
    street = models.CharField(max_length=255, null=True, blank=True)
    postal_code = models.CharField(max_length=20, null=True, blank=True)
    city_id = models.BigIntegerField(null=True, blank=True)

    # ---- step 3 (Story 1.9): dietary + allergies ----
    dietary_ids = models.JSONField(default=list, blank=True)
    allergy_ids = models.JSONField(default=list, blank=True)

    # ---- Story 6.7: partner referral attribution ----
    # Set when a social worker at a charity partner submits an
    # application on behalf of a member via the public referral form
    # (`/partners/refer/`). On approval the FK is copied onto the
    # resulting `User` so retention reporting (Story 6.2) can attribute
    # the member back to the referring partner.
    partner = models.ForeignKey(
        "partners.Partner",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        db_column="partner_id",
        related_name="referred_applications",
    )
    # Free-form payload for non-relational data carried alongside the
    # application — currently the referring social worker's name and
    # email (Story 6.7). Keeping this JSON avoids a per-feature schema
    # change every time we add a new optional capture field.
    metadata = models.JSONField(default=dict, blank=True)

    # ---- workflow ----
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_DRAFT
    )
    approved_by = models.BigIntegerField(null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    rejected_reason = models.TextField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "accounts"
        db_table = "applications"
        indexes = [
            models.Index(fields=["status", "-created_at"]),
            models.Index(fields=["email"]),
        ]

    def __str__(self) -> str:
        return f"Application<{self.id} {self.email} {self.status}>"
