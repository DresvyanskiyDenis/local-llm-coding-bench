# /// script
# requires-python = ">=3.11"
# dependencies = ["tzdata"]
# ///
"""Proof that every bug in B5's grade/key.json is a real defect.

One check per key id, each asserting the *correct* behaviour. A bug counts as
demonstrated only when its check FAILS against ``repo/src/billing.py`` and
PASSES against ``grade/ref_fixed/src/billing.py``.

Deterministic: every datetime is a fixed literal (2026-03-28/29, the European
spring-forward weekend), never ``now()``. ``tzdata`` is pinned as a dependency so
the DST check does not depend on the host having a system tz database.

Usage:
    uv run eval/tasks/B_review/B5_temporal_money/grade/verify_bugs.py
Exit 0 = every key entry demonstrated.
"""

from __future__ import annotations

import importlib.util
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

GRADE_DIR = Path(__file__).resolve().parent
BUGGY = GRADE_DIR.parent / "repo" / "src" / "billing.py"
FIXED = GRADE_DIR / "ref_fixed" / "src" / "billing.py"

BERLIN = ZoneInfo("Europe/Berlin")


def load_module(path: Path, name: str):
    sys.dont_write_bytecode = True  # never drop __pycache__ into the task's repo/
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def check_b1_float_equality(mod) -> None:
    """Instalments that add up to the invoice total must settle it."""
    assert mod.is_paid_in_full(0.30, [0.10, 0.20]) is True, (
        "0.10 + 0.20 does not settle a 0.30 invoice"
    )
    assert mod.is_paid_in_full(1.00, [0.70, 0.10, 0.20]) is True, (
        "0.70 + 0.10 + 0.20 does not settle a 1.00 invoice"
    )
    assert mod.is_paid_in_full(0.30, [0.10, 0.10]) is False, (
        "an underpaid invoice was reported as settled"
    )


def check_b2_dst_wall_clock(mod) -> None:
    """A 09:00 local run stays at 09:00 local across the spring-forward night."""
    current = datetime(2026, 3, 28, 9, 0, tzinfo=BERLIN)  # CET, day before the switch
    nxt = mod.next_billing_datetime(current)
    assert (nxt.year, nxt.month, nxt.day) == (2026, 3, 29), f"wrong date: {nxt}"
    assert (nxt.hour, nxt.minute) == (9, 0), (
        f"DST shifted the run to {nxt.hour:02d}:{nxt.minute:02d} local ({nxt})"
    )
    # And a run that does not straddle a transition is unaffected.
    plain = mod.next_billing_datetime(datetime(2026, 5, 10, 9, 0, tzinfo=BERLIN))
    assert (plain.day, plain.hour) == (11, 9), f"non-DST day shifted too: {plain}"


def check_b3_mutable_default(mod) -> None:
    """A caller that omits `ledger` must get a fresh map, not a shared one."""
    first = mod.accrue("cust-a", 100)
    second = mod.accrue("cust-b", 250)
    assert first == {"cust-a": 100}, f"first call returned {first}"
    assert second == {"cust-b": 250}, (
        f"the default ledger is shared between calls: {second}"
    )
    own = mod.accrue("cust-c", 5, {"cust-c": 10})
    assert own == {"cust-c": 15}, f"caller-supplied ledger mishandled: {own}"


CHECKS = [
    ("b1_float_equality", check_b1_float_equality),
    ("b2_dst_wall_clock", check_b2_dst_wall_clock),
    ("b3_mutable_default_ledger", check_b3_mutable_default),
]


def run(check, module):
    try:
        check(module)
    except AssertionError as exc:
        return False, str(exc)
    except Exception as exc:  # noqa: BLE001 - a crash is also "not correct"
        return False, f"{type(exc).__name__}: {exc}"
    return True, ""


def main() -> int:
    print(f"{'bug id':<32} {'buggy':<7} {'fixed':<7} verdict")
    print("-" * 78)
    ok = True
    for i, (bug_id, check) in enumerate(CHECKS):
        # Fresh imports per check: the mutable-default bug is stateful, so each
        # check must see a pristine module.
        buggy = load_module(BUGGY, f"b5_billing_buggy_{i}")
        fixed = load_module(FIXED, f"b5_billing_fixed_{i}")
        buggy_ok, buggy_detail = run(check, buggy)
        fixed_ok, fixed_detail = run(check, fixed)
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
