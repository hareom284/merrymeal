"""CSV row generator for the admin campaign-donations export (Story 5.8).

The export endpoint streams CSV with ``StreamingHttpResponse``, so this
module yields rows lazily instead of building one big list. The queryset is
iterated with ``chunk_size=500`` so a 10 000-donation campaign never lands
the whole table in memory at once — the reviewer specifically calls this out
as a pitfall in the story.

A separate ``amount_dollars`` column is included alongside ``amount_cents``
because the typical CSV consumer (accountants, board members) opens the file
in Excel and wants the human-readable figure. The cents column is the audit
trail; the dollars column is for reading.
"""

from __future__ import annotations

from collections.abc import Iterable

CSV_HEADER: list[str] = [
    "created_at",
    "donor_email",
    "amount_cents",
    "amount_dollars",
    "status",
    "payment_type",
    "transaction_id",
    "receipt_number",
    "is_recurring",
]


def _dollars(amount_cents: int) -> str:
    """Format integer cents as a plain ``D.DD`` string for the CSV column.

    The ``dollars`` template tag adds a ``$`` and thousands separator — fine
    for HTML, awkward for spreadsheets. CSV consumers want a raw number they
    can ``SUM()`` on, so the formatter here is bare.
    """
    sign = "-" if amount_cents < 0 else ""
    cents = abs(int(amount_cents))
    whole, remainder = divmod(cents, 100)
    return f"{sign}{whole}.{remainder:02d}"


def iter_csv_rows(qs) -> Iterable[list]:
    """Yield the header row, then one row per donation in ``qs``.

    ``qs`` should already be ordered (we sort by ``created_at`` ascending in
    the view so the CSV is reproducible). We re-iterate with
    ``iterator(chunk_size=500)`` to keep the working set bounded — the
    queryset itself is not evaluated until this generator is consumed by
    ``StreamingHttpResponse``.
    """
    yield CSV_HEADER
    for d in qs.iterator(chunk_size=500):
        yield [
            d.created_at.isoformat() if d.created_at else "",
            d.donor_email,
            d.amount_cents,
            _dollars(d.amount_cents),
            d.status,
            d.payment_type,
            d.transaction_id or "",
            d.receipt_number or "",
            "yes" if d.is_recurring else "no",
        ]
