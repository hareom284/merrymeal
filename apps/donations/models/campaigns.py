from django.db import models


class Campaign(models.Model):
    """Fundraising campaign — schema only.

    Business logic (raised totals, progress, lifecycle) lives in
    ``apps.donations.services.campaigns``. Per MerryMeal conventions models
    hold fields, ``Meta``, ``__str__`` and choice constants only.

    All money is stored as integer cents (``BigIntegerField``) — never
    floats, never ``DecimalField``. Stripe APIs talk cents, integer math is
    exact, and we never want a $0.005 rounding error on a receipt.
    """

    name = models.CharField(max_length=255)
    # ``slug`` is not in ``merrymeal_schema_corrected.sql`` (Sprint 09 adds it
    # via migration so the public donate page can deep-link as
    # ``/donate/?campaign=<slug>`` — Story 5.3). Schema doc will be updated
    # in a follow-up.
    slug = models.SlugField(max_length=255, unique=True)
    goal_cents = models.BigIntegerField()  # integer cents; never floats
    start_at = models.DateTimeField(null=True, blank=True)
    end_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    # Raw FK to ``partners.id`` (kept as ``BigIntegerField`` until Epic 02
    # promotes this to a proper ``ForeignKey(Partner)``). The schema's
    # ``fk_campaign_partner`` constraint is intentionally not enforced at
    # the ORM layer yet — see Sprint 09 story 5.1 acceptance criteria.
    partner_id = models.BigIntegerField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "donations"
        db_table = "campaigns"
        indexes = [
            models.Index(fields=["partner_id"], name="idx_campaign_partner"),
        ]

    def __str__(self) -> str:
        return self.name
