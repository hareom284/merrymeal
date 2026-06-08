from django.db import models

from apps.donations.models.campaigns import Campaign


class Donation(models.Model):
    """One donation pledge — schema only.

    State transitions (``pending`` → ``completed``, refund handling,
    receipt-number generation) live in ``apps.donations.services``. The
    model is intentionally bare: fields, ``Meta``, ``__str__`` and choice
    constants only — per MerryMeal conventions.

    Money is integer cents (``BigIntegerField``) — never ``DecimalField``,
    never ``FloatField``. Stripe APIs talk cents.

    Schema divergences from ``merrymeal_schema_corrected.sql`` (each one is
    deliberate; reviewer approves in the Story 5.2 PR):

    * ``donor_id`` is ``NULL``-able. The schema has it ``NOT NULL`` but the
      public donate page (Story 5.3) accepts anonymous gifts; donor
      identity is captured via ``donor_email`` and back-linked later if
      and when the email matches a future ``User``.
    * ``status`` adds ``cancelled`` to the schema's four-value ENUM.
      Subscriptions can be cancelled (Story 5.7) without the donation
      being refunded.
    * Several non-schema columns (``donor_email``, ``is_recurring``,
      ``stripe_subscription_id``, ``receipt_number``, ``updated_at``)
      support the donate / receipt / manage flows in Stories 5.3 – 5.7.
    """

    PAYMENT_TYPE_CHOICES = [
        ("card", "Card"),
        ("bank_transfer", "Bank transfer"),
        ("cash", "Cash"),
        ("paypal", "PayPal"),
    ]

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("completed", "Completed"),
        ("failed", "Failed"),
        ("refunded", "Refunded"),
        # ``cancelled`` is not in the SQL ENUM — added so a recurring
        # donation can be marked dormant by Story 5.7 without losing the
        # row (and the historical receipts) to a refund flow.
        ("cancelled", "Cancelled"),
    ]

    # Schema-aligned columns.
    # NOTE: schema declares ``donor_id NOT NULL`` — relaxed to nullable
    # here for anonymous donors. See class docstring.
    donor_id = models.BigIntegerField(null=True, blank=True)
    campaign = models.ForeignKey(
        Campaign,
        on_delete=models.PROTECT,  # never lose receipts because a campaign was deleted
        related_name="donations",
        db_column="campaign_id",
    )
    amount_cents = models.BigIntegerField()
    payment_type = models.CharField(max_length=20, choices=PAYMENT_TYPE_CHOICES)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="pending"
    )
    # Unique = Story 5.4's webhook idempotency hinge. Without it, a
    # ``checkout.session.completed`` re-fire would double-count the gift.
    transaction_id = models.CharField(
        max_length=191, null=True, blank=True, unique=True
    )

    # Extra columns for the donate / receipt / manage flows (not in the
    # SQL schema — Sprint 09 adds them).
    donor_email = models.EmailField()
    is_recurring = models.BooleanField(default=False)
    stripe_subscription_id = models.CharField(
        max_length=191, null=True, blank=True
    )
    # ``receipt_number`` is generated in series by the receipt service
    # (Story 5.5) as ``D<YYYY>-<NNNNNN>``. ``unique=True`` is the safety
    # net against a concurrent-issue race.
    receipt_number = models.CharField(
        max_length=32, null=True, blank=True, unique=True
    )

    created_at = models.DateTimeField(auto_now_add=True)
    # ``auto_now`` powers the "last charged" / "next charge" UI in Story
    # 5.7. Remember to include ``"updated_at"`` in any ``update_fields=``
    # save call (project convention — see CLAUDE.md).
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "donations"
        db_table = "donations"
        indexes = [
            models.Index(fields=["donor_id"], name="idx_don_donor"),
            # ``(campaign, status)`` covers the admin filter and Story
            # 5.8's "completed donations per campaign" digest query.
            models.Index(
                fields=["campaign", "status"], name="idx_don_campaign_status"
            ),
            # Story 5.7's manage-link lookup is by donor email; without
            # this index that path is a full table scan.
            models.Index(fields=["donor_email"], name="idx_don_email"),
        ]

    def __str__(self) -> str:
        return f"#{self.pk} {self.donor_email} {self.amount_cents}c {self.status}"
