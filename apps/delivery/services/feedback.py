"""Service: record a member's feedback for one delivery (Story 4.11).

`DeliveryFeedback` enforces a single feedback row per delivery via a
`UniqueConstraint(fields=["delivery"], name="uq_feedback_delivery")`
(see `apps/delivery/models/feedback.py`). The view layer guards against
the duplicate path with an early ``filter().exists()`` check, but two
near-simultaneous POSTs would still race past that guard — we catch the
resulting `IntegrityError` here and return the existing row so the
caller can always render the thanks card without branching on which
path it took.

Tags arrive as a list of choice keys from
`apps.delivery.forms.feedback.FeedbackForm.TAG_CHOICES`. We serialise
them as ``json.dumps({"tags": [...]})`` into the schema-locked
`DeliveryFeedback.note` `TEXT` column. A dedicated tags column is left
as a future migration (Epic 06's kitchen-feedback dashboards parse the
JSON once per aggregation).
"""
from __future__ import annotations

import json

from django.db import IntegrityError, transaction

from apps.delivery.models import Delivery, DeliveryFeedback


def record_feedback(
    delivery: Delivery, *, rating: int, tags: list[str]
) -> DeliveryFeedback:
    """Create (or return-existing) a feedback row for ``delivery``.

    The insert runs inside its own savepoint (`transaction.atomic()`
    context manager, not the bare decorator) so that an
    ``IntegrityError`` from the unique-on-``delivery_id`` constraint
    rolls back only the savepoint — leaving the outer test/request
    transaction usable for the follow-up ``SELECT``. Without the
    savepoint, Django marks the outer atomic block "needs_rollback"
    and the recovery query raises ``TransactionManagementError``.

    Raises
    ------
    ValueError
        ``rating`` outside 1..5. The view layer should already have
        rejected the form before calling, but the service double-checks
        in case it's invoked from a management command or test fixture.
    """
    if not 1 <= rating <= 5:
        raise ValueError("rating must be between 1 and 5")

    note = json.dumps({"tags": list(tags)})
    try:
        with transaction.atomic():
            return DeliveryFeedback.objects.create(
                delivery=delivery,
                rating=rating,
                note=note,
            )
    except IntegrityError:
        # A concurrent submit beat us to it — return the existing row
        # unchanged. Idempotent by design: the first rating wins, the
        # caller still gets a non-None feedback to render the thanks
        # partial.
        return DeliveryFeedback.objects.get(delivery=delivery)
