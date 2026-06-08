"""Donor-impact helper. Pure function — no DB, no IO.

Converts an integer-cents donation amount into the number of whole
meals the gift pays for, using ``MEAL_COST_CENTS`` (defaults to $3 per
meal). Read by:

* The donate page chips (Story 5.3) — "≈ 17 meals" caption.
* The thanks page (Story 5.5) — "your $50 = 17 meals" headline.
* The receipt email (Story 5.5) — same headline in the PDF / HTML body.
* The standalone ``/donations/impact/`` preview page (this story) —
  marketing-link target.

Settings are read **inside** the function (not cached at module load)
so ``@override_settings(MEAL_COST_CENTS=...)`` works in tests and ops
can rotate the conversion without restarting the process.
"""
from __future__ import annotations

from django.conf import settings


def meals_for_amount(amount_cents: int) -> int:
    """Return the floor of ``amount_cents / MEAL_COST_CENTS``.

    Raises ``TypeError`` for non-``int`` (including ``bool`` and
    ``float`` — money is integer cents everywhere). Raises
    ``ValueError`` for negative amounts; that's a programming bug
    upstream, not a refund.
    """
    # ``bool`` is a subclass of ``int`` in Python; ``True // 300 == 0``
    # would silently succeed without this guard. A caller passing
    # ``True`` is a bug, not a donation — fail loudly.
    if isinstance(amount_cents, bool) or not isinstance(amount_cents, int):
        raise TypeError(
            "meals_for_amount expects int cents, got "
            f"{type(amount_cents).__name__}"
        )
    if amount_cents < 0:
        raise ValueError("amount_cents must be non-negative")

    cost = int(getattr(settings, "MEAL_COST_CENTS", 300))
    if cost <= 0:
        # Defensive — ``MEAL_COST_CENTS=0`` would zero-divide. Treat
        # bad config the same way as bad input.
        raise ValueError("MEAL_COST_CENTS must be a positive integer")

    # Floor division — never ``/``, never ``round``. A donor who gives
    # $2.99 pays for zero meals; we don't round up to flatter them.
    return amount_cents // cost
