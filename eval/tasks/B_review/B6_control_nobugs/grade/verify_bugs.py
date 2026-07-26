# /// script
# requires-python = ">=3.11"
# dependencies = ["tzdata"]
# ///
"""Proof that B6's module is CORRECT — the false-positive control has no planted bug.

B3/B4/B5 ship a verify_bugs.py that proves each key entry is a real defect. B6's
key plants nothing, so this script proves the opposite claim, one check per
tempting construct listed in grade/CONTROL_RATIONALE.md: the memoised default
argument, the floor-division/modulo bucketing of pre-origin timestamps, the
double-checked locking, the delete-while-iterating prune, the negative-slice
tail, the integer half-up money rounding, the DST-crossing calendar day, and the
exception path that collects instead of aborting.

Deterministic: fixed timestamps (2026-03-28/29, the European spring-forward
weekend), fixed pseudo-random seed, no wall clock, no network. ``tzdata`` is
pinned so the DST check does not depend on a host tz database.

Usage:
    uv run eval/tasks/B_review/B6_control_nobugs/grade/verify_bugs.py
Exit 0 = every correctness claim holds (the control is clean).
"""

from __future__ import annotations

import importlib.util
import random
import sys
import threading
from datetime import datetime, timezone
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

GRADE_DIR = Path(__file__).resolve().parent
MODULE = GRADE_DIR.parent / "repo" / "src" / "rate_window.py"

BERLIN = ZoneInfo("Europe/Berlin")


def load_module(path: Path, name: str):
    sys.dont_write_bytecode = True  # never drop __pycache__ into the task's repo/
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def epoch_of(*args) -> int:
    """Epoch seconds of a UTC wall-clock instant, as an int."""
    return int(datetime(*args, tzinfo=timezone.utc).timestamp())


# --- one check per tempting construct -------------------------------------


def check_bucket_spec(mod) -> None:
    """bucket_start obeys its spec for every timestamp, including pre-origin ones.

    Independent characterisation, not a re-implementation: the returned start must
    contain the timestamp and must be an exact multiple of size_s away from the
    origin.
    """
    rng = random.Random(20260725)
    samples = [mod.WINDOW_ORIGIN, mod.WINDOW_ORIGIN - 1, mod.WINDOW_ORIGIN + 1, 0, 1, 59, 60]
    samples += [mod.WINDOW_ORIGIN - rng.randrange(1, 10_000_000) for _ in range(200)]
    samples += [mod.WINDOW_ORIGIN + rng.randrange(1, 10_000_000) for _ in range(200)]
    for size in (1, 7, 60, 300, 86_400):
        for ts in samples:
            start = mod.bucket_start(ts, size)
            assert start <= ts < start + size, f"bucket_start({ts}, {size}) = {start} excludes ts"
            assert (start - mod.WINDOW_ORIGIN) % size == 0, (
                f"bucket_start({ts}, {size}) = {start} is not aligned to the origin"
            )


def check_bucket_memo(mod) -> None:
    """The default-argument memo returns the same answers as a cold cache, and the
    bounded eviction never serves a stale or cross-size answer."""
    cold = {}
    for ts in (mod.WINDOW_ORIGIN + 125, mod.WINDOW_ORIGIN - 125, mod.WINDOW_ORIGIN):
        for size in (60, 300):
            cold[(ts, size)] = mod.bucket_start(ts, size, {})  # private, empty cache
    # Force the shared memo well past its eviction bound.
    for i in range(3 * mod._BUCKET_CACHE_MAX):
        mod.bucket_start(mod.WINDOW_ORIGIN + i * 60, 60)
    for (ts, size), expected in cold.items():
        got = mod.bucket_start(ts, size)
        assert got == expected, f"memo served {got} for ({ts}, {size}), cold cache says {expected}"
    assert len(mod.bucket_start.__defaults__[-1]) <= mod._BUCKET_CACHE_MAX, "memo is unbounded"


def check_parse_events_collects(mod) -> None:
    """Malformed events are collected, never swallowed and never fatal."""
    rejected: list = []
    raw = [
        {"tenant": " acme ", "ts": "1600000123", "units": 5},
        {"tenant": "acme", "ts": 1600000200, "units": "not-a-number"},
        {"ts": 1600000200, "units": 1},
        {"tenant": "  ", "ts": 1600000200, "units": 1},
        {"tenant": "beta", "ts": 1600000200, "units": -3},
        {"tenant": "beta", "ts": 1600000260, "units": 0},
    ]
    events = mod.parse_events(raw, rejected)
    assert events == [("acme", 1600000123, 5), ("beta", 1600000260, 0)], events
    assert len(rejected) == 4, f"expected 4 rejected events, got {len(rejected)}: {rejected}"
    assert rejected == [raw[1], raw[2], raw[3], raw[4]], "wrong events were rejected"


def check_concurrent_record(mod) -> None:
    """Double-checked locking creates exactly one counter and loses no unit."""
    meter = mod.Meter(size_s=60)
    threads_n, per_thread = 16, 250
    barrier = threading.Barrier(threads_n)
    errors: list[BaseException] = []
    seen_ids: set[int] = set()
    id_lock = threading.Lock()

    def worker():
        try:
            barrier.wait(timeout=30)
            for i in range(per_thread):
                meter.record("acme", 1_600_000_100 + (i % 3), 1)
            with id_lock:
                seen_ids.add(id(meter._counter_for("acme")))
        except BaseException as exc:  # noqa: BLE001 - surfaced below
            errors.append(exc)

    threads = [threading.Thread(target=worker) for _ in range(threads_n)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=60)
    assert not errors, f"worker raised: {errors[0]!r}"
    assert len(seen_ids) == 1, f"{len(seen_ids)} distinct counter objects for one tenant"
    snap = meter.snapshot("acme")
    assert sum(snap.values()) == threads_n * per_thread, (
        f"counted {sum(snap.values())}, expected {threads_n * per_thread}"
    )
    assert len(snap) == 1, f"the three timestamps span {len(snap)} buckets, expected 1"


def check_prune(mod) -> None:
    """prune drops exactly the aged-out buckets and forgets emptied tenants."""
    meter = mod.Meter(size_s=60)
    now = 1_600_003_600
    for k in range(10):
        meter.record("acme", now - k * 60, 1)
    meter.record("stale", now - 3600, 1)
    dropped = meter.prune(now, keep_windows=5)
    kept = sorted(meter.snapshot("acme"))
    assert len(kept) == 6, f"kept {len(kept)} buckets, expected 6 (current + 5)"
    assert min(kept) == mod.bucket_start(now, 60) - 5 * 60, f"wrong oldest kept bucket: {kept}"
    assert dropped == 5, f"reported {dropped} dropped buckets, expected 5"
    assert "stale" not in meter._counters, "a tenant with no buckets left was not forgotten"
    assert meter.snapshot("stale") == {}, "stale tenant still has buckets"


def check_tail_and_deltas(mod) -> None:
    """recent_totals/deltas handle the n<=0 and single-bucket edges correctly."""
    buckets = {300: 3, 100: 1, 200: 2, 400: 4}
    assert mod.recent_totals(buckets, 2) == [3, 4]
    assert mod.recent_totals(buckets, 0) == [], "n=0 must be empty, not the whole series"
    assert mod.recent_totals(buckets, -1) == []
    assert mod.recent_totals(buckets, 99) == [1, 2, 3, 4], "n > len must return everything"
    assert mod.recent_totals({}, 3) == []
    assert mod.deltas([1, 2, 4, 7]) == [1, 2, 3]
    assert mod.deltas([5]) == [], "one bucket has no delta"
    assert mod.deltas([]) == []


def check_billable_cents(mod) -> None:
    """Money is exact integer half-up cents, matching a Decimal reference."""
    def reference(units: int, rate: int) -> int:
        return int((Decimal(units) * Decimal(rate) / Decimal(1000)).quantize(
            Decimal("1"), rounding=ROUND_HALF_UP))

    rng = random.Random(4242)
    cases = [(0, 0), (1, 1), (500, 1), (1500, 1), (2500, 1), (999, 1000), (1, 1499), (1, 1500)]
    cases += [(rng.randrange(0, 10_000_000), rng.randrange(0, 5000)) for _ in range(500)]
    for units, rate in cases:
        got = mod.billable_cents(units, rate)
        assert isinstance(got, int), f"billable_cents returned {type(got).__name__}, not int"
        assert got == reference(units, rate), (
            f"billable_cents({units}, {rate}) = {got}, Decimal half-up says {reference(units, rate)}"
        )
    for bad in ((-1, 10), (10, -1)):
        try:
            mod.billable_cents(*bad)
        except ValueError:
            pass
        else:
            raise AssertionError(f"billable_cents{bad} should reject negative input")


def check_local_day_key(mod) -> None:
    """The calendar-day key follows the tenant's local day across a DST switch."""
    # 2026-03-29 is the European spring-forward day (02:00 -> 03:00 local).
    assert mod.local_day_key(epoch_of(2026, 3, 28, 23, 30), "Europe/Berlin") == "2026-03-29"
    assert mod.local_day_key(epoch_of(2026, 3, 29, 21, 59), "Europe/Berlin") == "2026-03-29"
    assert mod.local_day_key(epoch_of(2026, 3, 29, 22, 30), "Europe/Berlin") == "2026-03-30"
    # 2026-10-25 is the fall-back day (a 25-hour local day).
    assert mod.local_day_key(epoch_of(2026, 10, 25, 22, 30), "Europe/Berlin") == "2026-10-25"
    assert mod.local_day_key(epoch_of(2026, 10, 25, 23, 30), "Europe/Berlin") == "2026-10-26"
    # A different zone, same instant, different day.
    instant = epoch_of(2026, 3, 29, 0, 30)
    assert mod.local_day_key(instant, "UTC") == "2026-03-29"
    assert mod.local_day_key(instant, "Pacific/Auckland") == "2026-03-29"
    assert mod.local_day_key(epoch_of(2026, 3, 29, 12, 30), "Pacific/Auckland") == "2026-03-30"


CHECKS = [
    ("bucket_start spec, incl. pre-origin", check_bucket_spec),
    ("memoised default arg is consistent", check_bucket_memo),
    ("parse_events collects, never aborts", check_parse_events_collects),
    ("double-checked locking is correct", check_concurrent_record),
    ("prune deletes while iterating safely", check_prune),
    ("tail slice + n-1 deltas edges", check_tail_and_deltas),
    ("integer half-up money vs Decimal", check_billable_cents),
    ("local calendar day across DST", check_local_day_key),
]


def main() -> int:
    module = load_module(MODULE, "b6_rate_window")
    print(f"{'correctness check':<40} result")
    print("-" * 78)
    ok = True
    for label, check in CHECKS:
        try:
            check(module)
        except AssertionError as exc:
            ok = False
            print(f"{label:<40} FAIL")
            print(f"{'':<40} {exc}")
        except Exception as exc:  # noqa: BLE001
            ok = False
            print(f"{label:<40} ERROR")
            print(f"{'':<40} {type(exc).__name__}: {exc}")
        else:
            print(f"{label:<40} PASS")
    print()
    print("CONTROL VERIFIED: no defect in src/rate_window.py" if ok
          else "CONTROL BROKEN: the 'no-bug' file misbehaves")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
