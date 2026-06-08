"""Donor history — read-only query for the logged-in donor.

Story 6.3.

Single entry point :func:`donor_history` returns every ``Donation`` row
whose ``donor_email`` matches the requesting user's email
(case-insensitive). The view layer is responsible for passing
``request.user``; this module never trusts an arbitrary email or id.

Why email and not ``donor_id``
------------------------------
The schema-locked ``donations.donor_id`` column is *nullable* (Sprint
09 — Story 5.2): anonymous public donate-page submissions land in the
table without a User row attached, and only later (if/when an account
is created with the same email) does the back-link happen. The donor
history page must work for donors who pre-existed the donation, donors
who created an account after donating, and donors whose row simply
hasn't been back-linked yet — all three cases share the
``donor_email`` column. Matching on email is the only reliable bridge.

Why every status (not just ``completed`` / ``refunded``)
-------------------------------------------------------
A ``pending`` donation that never landed, or a ``failed`` charge, is
information the donor needs *more* than the office does — they can
retry or contact support. We render every status and let the template
attach a badge so the donor sees what happened. This is a deliberate
divergence from the original 6.3 spec, which proposed hiding non-final
statuses to keep the office's books clean; the trade-off goes in
favour of donor transparency.
"""
from __future__ import annotations


def donor_history(user) -> list:
    """Return every donation for ``user``, newest first.

    Case-insensitive match on ``donor_email`` so donors who typed
    ``Margaret@Example.com`` into the donate form still see the row
    when they log in with a normalised ``margaret@example.com``.

    The caller MUST pass ``request.user``; passing an arbitrary email
    or id would bypass the role gate enforced by the view.
    """
    from apps.donations.models import Donation

    if not getattr(user, "email", None):
        # Defensive — an authenticated user should always have an
        # email, but a misconfigured fixture or future SSO path might
        # not. Returning ``[]`` keeps the page renderable.
        return []

    return list(
        Donation.objects.filter(donor_email__iexact=user.email)
        .select_related("campaign")
        .order_by("-created_at")
    )


def list_for_fy(user, fy: int) -> tuple[list[dict], int]:
    """Return ``(rows, total_cents)`` of receiptable donations for ``user``.

    Story 6.4. Used by the FY tax-receipt page. Rows are dicts (not
    model instances) so the template and the JSON serializer share one
    shape. Sorted chronologically — accountants prefer "oldest first"
    when transcribing into a tax return.

    Why ``status == 'completed'`` only
    ----------------------------------
    Pending charges have not landed; failed and cancelled charges
    were never income; refunded donations have been returned in full
    so they are not deductible. Only ``completed`` rows count as a
    tax-deductible gift.

    Why ``donor_email__iexact`` (not ``donor_id``)
    -----------------------------------------------
    Same reason as :func:`donor_history` — Sprint 09 accepts anonymous
    donations whose ``donor_id`` is NULL until the donor creates an
    account with the matching email. Filtering on email keeps the
    receipt complete in every case.

    Why ``created_at__date``
    ------------------------
    Django evaluates the ``__date`` lookup in the project ``TIME_ZONE``
    (``Australia/Melbourne``), so a donation at ``2025-06-30 23:59:59``
    Melbourne time falls into FY 2025 even though the underlying UTC
    column reads ``2025-06-30 13:59:59``. The boundary tests pin this.
    """
    from apps.dashboards.services.fy import fy_period
    from apps.donations.models import Donation

    if not getattr(user, "email", None):
        return [], 0

    start, end = fy_period(fy)
    qs = (
        Donation.objects.filter(
            donor_email__iexact=user.email,
            status="completed",
            created_at__date__gte=start,
            created_at__date__lte=end,
        )
        .select_related("campaign")
        .order_by("created_at")
    )
    rows = [
        {
            "id": d.id,
            "created_at": d.created_at,
            "amount_cents": d.amount_cents,
            "campaign_name": d.campaign.name,
            "transaction_id": d.transaction_id or "",
            "receipt_number": d.receipt_number or "",
        }
        for d in qs
    ]
    total = sum(r["amount_cents"] for r in rows)
    return rows, total
