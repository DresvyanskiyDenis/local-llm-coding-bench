"""Reference-fixed copy of ``repo/src/billing.py``.

Identical to the task's module except for the three planted bugs listed in
``grade/key.json``, each fixed in place and marked ``FIX bN`` below. Used only by
``grade/verify_bugs.py`` to prove that every key entry is a real defect: the
checks fail against ``repo/`` and pass against this file.
"""

from __future__ import annotations

from datetime import datetime, timedelta


def is_paid_in_full(invoice_total: float, payments: list[float]) -> bool:
    """True when ``payments`` settle ``invoice_total``.

    Partial payments are common: an invoice is settled by whatever mix of
    instalments adds up to its total.
    """
    # FIX b1: `sum(payments) == invoice_total` compared binary floats exactly, so
    # 0.10 + 0.20 never settled a 0.30 invoice. Compare in whole cents instead.
    return round(sum(payments) * 100) == round(invoice_total * 100)


def outstanding_balance(invoice_total: float, payments: list[float]) -> float:
    """Euros still owed on the invoice, rounded to cents, never negative."""
    return max(0.0, round(invoice_total - sum(payments), 2))


def next_billing_datetime(current: datetime, days: int = 1) -> datetime:
    """Return the next billing run after ``current``.

    ``current`` is a timezone-aware datetime in the customer's local timezone.
    The next run is the *same wall-clock time* ``days`` later: a run at 09:00
    local stays at 09:00 local even when a DST transition falls in between.
    """
    # FIX b2: converting to UTC, adding, and converting back is *absolute*
    # (elapsed-time) arithmetic, which moves the wall clock by an hour across a
    # DST boundary. Adding the timedelta to the aware local datetime directly is
    # wall-clock arithmetic, which is what the SLA describes.
    return current + timedelta(days=days)


def accrue(customer_id: str, amount_cents: int, ledger: dict | None = None) -> dict:
    """Add ``amount_cents`` to ``customer_id``'s running accrual.

    Returns the accrual map. Callers that track several customers pass their own
    ``ledger`` in; callers that do not get a fresh map for this call.
    """
    # FIX b3: `ledger: dict = {}` was a mutable default, shared by every call that
    # omitted the argument, so accruals leaked between unrelated customers.
    if ledger is None:
        ledger = {}
    ledger[customer_id] = ledger.get(customer_id, 0) + amount_cents
    return ledger
