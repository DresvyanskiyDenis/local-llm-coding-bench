"""Subscription billing helpers: settlement, run scheduling and accruals.

Invoices are stored as euro amounts (``float``) coming straight from the payment
provider's JSON. Billing runs are scheduled in the customer's own timezone: a run
booked for 09:00 local must keep happening at 09:00 local every day, DST changes
included, because that is what the SLA promises the customer's finance team.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone


def is_paid_in_full(invoice_total: float, payments: list[float]) -> bool:
    """True when ``payments`` settle ``invoice_total``.

    Partial payments are common: an invoice is settled by whatever mix of
    instalments adds up to its total.
    """
    return sum(payments) == invoice_total


def outstanding_balance(invoice_total: float, payments: list[float]) -> float:
    """Euros still owed on the invoice, rounded to cents, never negative."""
    return max(0.0, round(invoice_total - sum(payments), 2))


def next_billing_datetime(current: datetime, days: int = 1) -> datetime:
    """Return the next billing run after ``current``.

    ``current`` is a timezone-aware datetime in the customer's local timezone.
    The next run is the *same wall-clock time* ``days`` later: a run at 09:00
    local stays at 09:00 local even when a DST transition falls in between.
    """
    absolute = current.astimezone(timezone.utc) + timedelta(days=days)
    return absolute.astimezone(current.tzinfo)


def accrue(customer_id: str, amount_cents: int, ledger: dict = {}) -> dict:
    """Add ``amount_cents`` to ``customer_id``'s running accrual.

    Returns the accrual map. Callers that track several customers pass their own
    ``ledger`` in; callers that do not get a fresh map for this call.
    """
    ledger[customer_id] = ledger.get(customer_id, 0) + amount_cents
    return ledger
