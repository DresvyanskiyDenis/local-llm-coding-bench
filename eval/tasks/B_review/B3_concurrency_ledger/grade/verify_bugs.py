# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Proof that every bug in B3's grade/key.json is a real defect.

For each key entry there is exactly one check that asserts the *correct*
behaviour. A bug counts as demonstrated only when its check FAILS against
``repo/src/ledger.py`` and PASSES against ``grade/ref_fixed/src/ledger.py``
(the same module with only that bug class fixed). No blanket "the module
misbehaves" assertion: one check per key id.

Deterministic by construction -- no sleeps-as-synchronisation, no wall clock,
no network. The race is forced with a ``threading.Barrier`` parked inside the
read-modify-write window rather than being raced for.

Usage:
    uv run eval/tasks/B_review/B3_concurrency_ledger/grade/verify_bugs.py
Exit 0 = every key entry demonstrated.
"""

from __future__ import annotations

import importlib.util
import os
import sys
import tempfile
import threading
from datetime import date
from pathlib import Path

GRADE_DIR = Path(__file__).resolve().parent
BUGGY = GRADE_DIR.parent / "repo" / "src" / "ledger.py"
FIXED = GRADE_DIR / "ref_fixed" / "src" / "ledger.py"

DAY = date(2026, 1, 1)


def load_module(path: Path, name: str):
    sys.dont_write_bytecode = True  # never drop __pycache__ into the task's repo/
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def open_fd_count() -> int:
    for d in ("/proc/self/fd", "/dev/fd"):
        if os.path.isdir(d):
            return len(os.listdir(d))
    raise RuntimeError("no /proc/self/fd or /dev/fd on this platform")


class BarrierDay:
    """Stand-in for ``datetime.date`` whose first ``isoformat()`` call per thread
    parks on a barrier. That pins both workers inside the read-modify-write window
    at the same time, so the lost update is forced rather than raced for."""

    def __init__(self, barrier: threading.Barrier) -> None:
        self._barrier = barrier
        self._local = threading.local()

    def isoformat(self) -> str:
        if not getattr(self._local, "synced", False):
            self._local.synced = True
            try:
                self._barrier.wait(timeout=2.0)
            except threading.BrokenBarrierError:
                pass  # correct code holds the lock here, so the barrier never fills
        return DAY.isoformat()


def check_b1_race_lost_update(mod, tmp: Path) -> None:
    """Two workers crediting 100 cents each must leave a balance of 200."""
    ledger = mod.Ledger(tmp / "race")
    day = BarrierDay(threading.Barrier(2))
    errors: list[BaseException] = []

    def worker():
        try:
            ledger.apply_transaction("acct-1", 100, day)
        except BaseException as exc:  # noqa: BLE001 - surfaced below, never swallowed
            errors.append(exc)

    threads = [threading.Thread(target=worker) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=20)
    ledger.close()
    assert not errors, f"worker raised: {errors[0]!r}"
    balance = ledger.balance("acct-1")
    assert balance == 200, f"lost update: balance is {balance}, expected 200"
    assert len(ledger._journal) == 2, f"journal has {len(ledger._journal)} entries, expected 2"


def check_b2_off_by_one_recent(mod, tmp: Path) -> None:
    """recent_entries(count) must return exactly the last ``count`` entries."""
    ledger = mod.Ledger(tmp / "recent")
    for i in range(5):
        ledger.apply_transaction("acct-1", i + 1, DAY)
    ledger.close()
    recent = ledger.recent_entries(2)
    assert len(recent) == 2, f"recent_entries(2) returned {len(recent)} entries"
    assert [e["amount_cents"] for e in recent] == [4, 5], (
        f"recent_entries(2) returned {[e['amount_cents'] for e in recent]}, expected [4, 5]"
    )


def check_b3_audit_fd_leak(mod, tmp: Path) -> None:
    """close() must release the audit file descriptors it opened."""
    keep_alive = []
    warm = mod.Ledger(tmp / "warm")
    warm.apply_transaction("acct-1", 1, DAY)
    warm.close()
    keep_alive.append(warm)

    before = open_fd_count()
    for i in range(20):
        ledger = mod.Ledger(tmp / f"leak-{i}")
        ledger.apply_transaction("acct-1", 1, DAY)
        ledger.close()
        keep_alive.append(ledger)  # still referenced: only close() can free the fd
    leaked = open_fd_count() - before
    assert leaked < 5, f"close() leaked {leaked} file descriptors across 20 ledgers"


CHECKS = [
    ("b1_race_lost_update", check_b1_race_lost_update),
    ("b2_off_by_one_recent_entries", check_b2_off_by_one_recent),
    ("b3_audit_handle_leak", check_b3_audit_fd_leak),
]


def run(check, module, label: str):
    with tempfile.TemporaryDirectory(prefix=f"b3-{label}-") as tmp:
        try:
            check(module, Path(tmp))
        except AssertionError as exc:
            return False, str(exc)
        except Exception as exc:  # noqa: BLE001 - a crash is also "not correct"
            return False, f"{type(exc).__name__}: {exc}"
    return True, ""


def main() -> int:
    buggy = load_module(BUGGY, "b3_ledger_buggy")
    fixed = load_module(FIXED, "b3_ledger_fixed")

    print(f"{'bug id':<32} {'buggy':<7} {'fixed':<7} verdict")
    print("-" * 78)
    ok = True
    for bug_id, check in CHECKS:
        buggy_ok, buggy_detail = run(check, buggy, f"{bug_id}-buggy")
        fixed_ok, fixed_detail = run(check, fixed, f"{bug_id}-fixed")
        demonstrated = (not buggy_ok) and fixed_ok
        ok = ok and demonstrated
        verdict = "demonstrated" if demonstrated else "NOT DEMONSTRATED"
        print(f"{bug_id:<32} {'FAIL' if not buggy_ok else 'pass':<7} "
              f"{'PASS' if fixed_ok else 'fail':<7} {verdict}")
        if buggy_detail:
            print(f"{'':<32} buggy: {buggy_detail}")
        if not fixed_ok:
            print(f"{'':<32} fixed: {fixed_detail}")
    print()
    print("ALL BUGS DEMONSTRATED" if ok else "SOME KEY ENTRIES ARE NOT DEMONSTRATED")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
