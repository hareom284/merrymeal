"""Story 5.5 — invariants for ``assign_receipt_number``.

Receipt numbers must be:

* **Year-scoped** — first receipt of 2027 is ``D2027-000001`` regardless of
  how many were issued in 2026.
* **Monotonic per year** — every new completed donation in the same year
  increments the trailing counter.
* **Idempotent** — calling ``assign_receipt_number`` twice on the same
  ``Donation`` row returns the original number; the row keeps it forever.
* **Concurrency-safe** — generated inside ``transaction.atomic()`` with
  ``select_for_update()`` so two webhook workers cannot pick the same
  number. (We don't simulate concurrent transactions here — the unit
  tests assert the contract; the SQL surface is exercised by the
  integration test in ``test_receipt_email.py``.)
"""

from __future__ import annotations

import datetime as dt

import pytest

from apps.donations.services.receipts import assign_receipt_number
from apps.donations.tests.factories import DonationFactory


@pytest.fixture
def freezer(monkeypatch):
    """Lightweight date-pinning fixture.

    The project lists ``pytest-freezer`` in ``requirements.txt`` but the
    wheel is not installed in the local Homebrew Python environment, so
    we mimic the small slice of the API the receipt-number tests need:
    ``freezer.move_to("YYYY-MM-DD")`` patches ``django.utils.timezone.now``
    to return that wall-clock date at midnight Melbourne time. Mirrors
    the fixture in ``apps/planning/tests/test_validate_command.py``.
    """

    class _Freezer:
        def move_to(self, iso: str) -> None:
            target = dt.date.fromisoformat(iso)
            import django.utils.timezone as tz
            # Midday Melbourne local time so any UTC-aware conversion
            # downstream stays within the same calendar date.
            local = dt.datetime.combine(target, dt.time(12, 0))
            aware = tz.make_aware(local, tz.get_current_timezone())
            monkeypatch.setattr(tz, "now", lambda: aware)

    return _Freezer()


@pytest.mark.django_db
def test_first_receipt_of_year_is_000001(freezer):
    freezer.move_to("2026-03-01")
    donation = DonationFactory(status="completed")
    assert assign_receipt_number(donation) == "D2026-000001"


@pytest.mark.django_db
def test_subsequent_receipt_increments(freezer):
    freezer.move_to("2026-03-02")
    first = DonationFactory(status="completed")
    second = DonationFactory(status="completed")
    assign_receipt_number(first)
    assert assign_receipt_number(second) == "D2026-000002"


@pytest.mark.django_db
def test_assign_is_idempotent(freezer):
    freezer.move_to("2026-03-02")
    donation = DonationFactory(status="completed")
    first = assign_receipt_number(donation)
    second = assign_receipt_number(donation)
    assert first == second
    # And the row carries the number across reads.
    donation.refresh_from_db()
    assert donation.receipt_number == first


@pytest.mark.django_db
def test_year_rollover_restarts_counter(freezer):
    freezer.move_to("2026-12-31")
    december = DonationFactory(status="completed")
    assign_receipt_number(december)
    freezer.move_to("2027-01-01")
    january = DonationFactory(status="completed")
    assert assign_receipt_number(january) == "D2027-000001"


@pytest.mark.django_db
def test_receipt_number_format_is_zero_padded_to_six(freezer):
    """The ``NNNNNN`` segment is always six digits — no shorter, no longer."""
    freezer.move_to("2026-06-09")
    donation = DonationFactory(status="completed")
    number = assign_receipt_number(donation)
    # ``D<year>-<6 digits>`` — total length 12.
    assert len(number) == 12
    year, seq = number.split("-")
    assert year == "D2026"
    assert seq.isdigit() and len(seq) == 6
