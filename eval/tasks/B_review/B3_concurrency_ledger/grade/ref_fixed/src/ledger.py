"""Reference-fixed copy of ``repo/src/ledger.py``.

Identical to the task's module except for the three planted bugs listed in
``grade/key.json``, each fixed in place and marked ``FIX bN`` below. Used only by
``grade/verify_bugs.py`` to prove that every key entry is a real defect: the
checks fail against ``repo/`` and pass against this file.
"""

from __future__ import annotations

import json
import threading
from datetime import date
from pathlib import Path


class Ledger:
    """A thread-safe account ledger.

    Every public method is safe to call from several worker threads at once.
    """

    def __init__(self, audit_dir: str | Path) -> None:
        self._audit_dir = Path(audit_dir)
        self._audit_dir.mkdir(parents=True, exist_ok=True)
        self._balances: dict[str, int] = {}
        self._journal: list[dict] = []
        self._handles: dict[str, object] = {}
        self._lock = threading.Lock()
        self._closed = False

    def apply_transaction(self, account: str, amount_cents: int, day: date) -> int:
        """Add ``amount_cents`` to ``account``, journal the movement and return
        the account's new balance."""
        if self._closed:
            raise RuntimeError("ledger is closed")
        # FIX b1: the read-modify-write of the balance happens entirely under the
        # lock, so two workers can no longer both read the same stale balance.
        with self._lock:
            balance = self._balances.get(account, 0)
            entry = {
                "account": account,
                "amount_cents": amount_cents,
                "day": day.isoformat(),
                "balance_before": balance,
            }
            self._balances[account] = balance + amount_cents
            self._journal.append(entry)
        self._append_audit(day, entry)
        return balance + amount_cents

    def balance(self, account: str) -> int:
        """Current balance of ``account``, in cents."""
        with self._lock:
            return self._balances.get(account, 0)

    def recent_entries(self, count: int = 10) -> list[dict]:
        """Return the ``count`` most recent journal entries, oldest first."""
        if count <= 0:
            return []
        with self._lock:
            start = max(0, len(self._journal) - count)  # FIX b2: was len - count - 1
            return self._journal[start:]

    def _append_audit(self, day: date, entry: dict) -> None:
        """Mirror ``entry`` into that day's audit file, opening it on first use."""
        key = day.isoformat()
        with self._lock:
            handle = self._handles.get(key)
            if handle is None:
                handle = open(self._audit_dir / f"audit-{key}.log", "a", encoding="utf-8")
                self._handles[key] = handle
            handle.write(json.dumps(entry) + "\n")

    def close(self) -> None:
        """Flush and release every audit file this ledger opened."""
        with self._lock:
            for handle in self._handles.values():
                handle.flush()
                handle.close()  # FIX b3: the handles were only flushed, never closed
            self._handles.clear()
            self._closed = True
