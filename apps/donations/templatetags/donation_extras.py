"""Template filters for the donations app.

The single conversion point between integer-cents (database / API) and the
human-facing dollar string lives here. Every monetary display in the admin,
donate page, receipt email and manage page renders through ``dollars`` —
keeping the format consistent and the "money is integer cents" rule
enforced (floats raise ``TypeError`` at the boundary).
"""

from django import template

from apps.donations.services.impact import meals_for_amount

register = template.Library()


@register.filter
def dollars(amount_cents):
    """Format integer cents as ``$1,234.56``.

    ``None`` is treated as zero so unset goals render as ``$0.00`` instead
    of blowing up the admin progress bar. Floats raise ``TypeError`` on
    purpose — money is integer cents everywhere, and a float arriving here
    means a caller upstream is doing the wrong thing (Stripe APIs talk
    cents, the DB stores cents, the Decimal-to-int conversion has to
    happen at the parser, not the template).
    """
    if amount_cents is None:
        amount_cents = 0
    # ``bool`` is a subclass of ``int`` in Python; explicitly reject it so
    # ``dollars(True)`` doesn't silently render as ``$0.01``.
    if isinstance(amount_cents, bool):
        raise TypeError("dollars() expects int, got bool")
    if isinstance(amount_cents, float):
        raise TypeError("Money is integer cents — got float. Fix the caller.")
    if not isinstance(amount_cents, int):
        raise TypeError(
            f"dollars() expects int, got {type(amount_cents).__name__}"
        )
    sign = "-" if amount_cents < 0 else ""
    cents = abs(amount_cents)
    whole, remainder = divmod(cents, 100)
    return f"{sign}${whole:,}.{remainder:02d}"


@register.filter
def meals_for(amount_cents):
    """Return how many meals ``amount_cents`` buys at $3 per meal.

    Forgiving variant of ``apps.donations.services.impact.meals_for_amount``
    — templates should never crash on a missing or stringly-typed value.
    ``None`` / empty string / non-numeric input all return ``0`` so the
    donate-page chip captions render cleanly even when the upstream
    context is partly populated.

    The service stays strict (raising on floats and negatives) because
    the receipt + thanks page need that protection; the template tag is
    the relaxed boundary.
    """
    if amount_cents in (None, ""):
        return 0
    try:
        # ``int(...)`` coerces ``"5000"`` -> 5000 (string filter args)
        # and rejects ``"12.5"`` with ``ValueError`` — which we catch.
        return meals_for_amount(int(amount_cents))
    except (TypeError, ValueError):
        return 0
