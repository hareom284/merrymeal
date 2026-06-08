"""Story 5.7 — magic-link token model.

The recurring-donation management flow uses a stateless signed token in
the URL (``django.core.signing.dumps`` with a 30-min ``max_age``) **and**
a tiny DB row that records the ``token_id`` portion of the payload. The
DB row exists for one reason: to flip ``used_at`` on first click so a
re-played link returns 410 Gone instead of granting access a second time.

Two layers of defence:

* The signed string handles **expiry + tamper resistance**. Without a
  valid signature, ``loads`` raises ``BadSignature``.
* The ``MagicLinkToken`` row handles **single-use**. ``used_at`` is set
  by the verify-side service the first time the token is consumed; any
  subsequent call raises ``BadSignature``.

Schema-only — no business methods (MerryMeal convention). The ``used_at``
flip lives in ``apps.donations.services.manage.verify_token``.

Retention: rows are kept after ``used_at`` is set so re-play attempts
are auditable. A future periodic Q2 task prunes rows older than 30 days
(out of scope for this story).
"""

from __future__ import annotations

import uuid

from django.db import models


def _generate_token_id() -> str:
    """Default factory for ``MagicLinkToken.token_id``.

    A module-level function (not a lambda) so Django's migration
    autodetector can serialise the default cleanly — lambdas trip the
    ``Cannot serialize`` migration error.
    """
    return uuid.uuid4().hex


class MagicLinkToken(models.Model):
    """Single-use, 30-min token for the donation-management magic-link flow."""

    # ``token_id`` is the random portion stamped into the signed URL
    # payload. The signed string includes ``{"email": ..., "tid": ...}``;
    # verify-time we match ``tid`` against this column to find the row.
    token_id = models.CharField(
        max_length=64, unique=True, default=_generate_token_id
    )
    # ``email`` is duplicated into the row (also in the signed payload)
    # so an audit query can answer "how many magic links did <email>
    # request this week?" without decoding every signed string.
    email = models.EmailField(db_index=True)
    # ``used_at`` is the single-use hinge. ``NULL`` = unused; non-NULL =
    # already consumed (any subsequent verify must fail).
    used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "donations"
        db_table = "donation_magic_link_tokens"

    def __str__(self) -> str:
        state = "used" if self.used_at else "unused"
        return f"{self.email} ({state})"
