"""Story 5.5 — receipt-number assignment + transactional receipt email.

Two public helpers, both safe to call inside the webhook-triggered status
transition in :mod:`apps.donations.services.payments`:

* :func:`assign_receipt_number` — generate (or return the already-assigned)
  ``D<YYYY>-<NNNNNN>`` number for a ``Donation``. Idempotent — calling
  twice on the same row returns the original number.

* :func:`send_receipt_email` — render the HTML + plain-text receipt and
  dispatch it via ``EmailMultiAlternatives``. Caller is responsible for
  one-shot semantics; we expose :func:`_complete_and_notify` in
  ``payments.py`` as the single transition point so re-fired webhooks
  cannot double-send.

Conventions:

* Money is integer cents (``donation.amount_cents``). The dollar render
  is delegated to the ``dollars`` template filter inside the email
  templates — never built ad-hoc in Python.
* Timestamps render in ``Australia/Melbourne``. ``donation.created_at``
  is stored UTC (``USE_TZ=True``); the template context exposes a
  pre-localized ``local_dt`` so neither template has to remember the
  conversion.
* Receipt numbers are year-scoped (``D<YYYY>-<seq>``). The counter resets
  to 1 on January 1st in Melbourne local time. Concurrency is guarded by
  ``transaction.atomic()`` + ``select_for_update()`` over the matching
  ``receipt_number__startswith`` set — Postgres / MySQL both block a
  second worker on the same prefix until the first commits.
"""

from __future__ import annotations

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.db import transaction
from django.template.loader import render_to_string
from django.utils import timezone

from apps.donations.models import Donation


def assign_receipt_number(donation: Donation) -> str:
    """Return ``donation.receipt_number``, generating it if missing.

    Idempotent — if ``donation.receipt_number`` is already set, return it
    unchanged. Otherwise pick the next available ``D<year>-<seq>`` for
    the donation's year (derived from ``created_at`` in Melbourne local
    time) and persist it.

    The save uses ``update_fields=["receipt_number", "updated_at"]`` so
    we don't churn unrelated columns. ``updated_at`` is included
    explicitly because ``auto_now=True`` only fires when the field is in
    ``update_fields`` (project convention — see CLAUDE.md).
    """
    if donation.receipt_number:
        return donation.receipt_number

    # ``created_at`` is set by ``auto_now_add`` on first save, so a row
    # passed in fresh will already have it. Falling back to ``now()`` is
    # belt-and-braces for callers that haven't saved yet.
    anchor = donation.created_at or timezone.now()
    year = timezone.localtime(anchor).year
    prefix = f"D{year}-"

    with transaction.atomic():
        # ``select_for_update`` on the matching prefix set blocks any
        # concurrent transaction that tries to read the same year's
        # tail until we commit. ``order_by("-receipt_number")`` exploits
        # the fact that zero-padded six-digit sequences sort
        # lexicographically the same way they sort numerically — true
        # for any year-scoped run that never exceeds 999,999 receipts.
        last = (
            Donation.objects
            .select_for_update()
            .filter(receipt_number__startswith=prefix)
            .order_by("-receipt_number")
            .first()
        )
        if last is None:
            seq = 1
        else:
            # Trailing segment after the ``D<year>-`` prefix.
            seq = int(last.receipt_number.split("-", 1)[1]) + 1

        donation.receipt_number = f"{prefix}{seq:06d}"
        donation.save(update_fields=["receipt_number", "updated_at"])

    return donation.receipt_number


def send_receipt_email(donation: Donation) -> None:
    """Render + send the receipt email for ``donation``.

    Assigns a receipt number first (so a crash between the assign and
    the send leaves the row numbered — the next run replays cleanly via
    the idempotent ``assign_receipt_number``). Templates live at
    ``templates/donations/emails/receipt.{txt,html}``.

    Caller (``apps.donations.services.payments._complete_and_notify``)
    guarantees one-shot semantics by gating on
    ``donation.receipt_number`` — see that function's docstring.
    """
    # Local import — ``apps.donations.services.impact`` is a leaf module
    # but importing at module top would couple receipt rendering to the
    # impact helper at import time. Local keeps the dependency lazy.
    from apps.donations.services.impact import meals_for_amount

    receipt_number = assign_receipt_number(donation)
    local_dt = timezone.localtime(donation.created_at or timezone.now())

    ctx = {
        "donation": donation,
        "campaign": donation.campaign,
        "meals": meals_for_amount(donation.amount_cents),
        "abn": settings.DONATIONS_CHARITY_ABN,
        "address": settings.DONATIONS_CHARITY_ADDRESS,
        "receipt_number": receipt_number,
        "local_dt": local_dt,
    }

    text_body = render_to_string("donations/emails/receipt.txt", ctx)
    html_body = render_to_string("donations/emails/receipt.html", ctx)

    msg = EmailMultiAlternatives(
        subject=f"Your MerryMeal receipt — {receipt_number}",
        body=text_body,
        from_email=settings.DONATIONS_FROM_EMAIL,
        to=[donation.donor_email],
    )
    msg.attach_alternative(html_body, "text/html")
    msg.send()
