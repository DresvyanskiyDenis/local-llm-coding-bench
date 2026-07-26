# B6 — why `src/rate_window.py` is correct

B6 is the false-positive control: **nothing is planted**. `grade/key.json` is
`{"control": true, "bugs": []}`, so `review_grader.py` reports `recall: null`,
`precision: 1.0` if the model reported nothing and `0.0` otherwise, plus
`false_positive_rate`.

A control is only worth running if it is *tempting* — a reviewer must want to flag
something. Every construct below was chosen because it pattern-matches a classic
Python defect while being correct here. This document is the defence if a model's
"finding" is later disputed; `grade/verify_bugs.py` is the executable half of the
same argument (8 checks, all passing, one per construct).

| # | Line(s) | Looks like | Why it is correct |
|---|---|---|---|
| 1 | 26, 33–41 | mutable default argument (`_cache: dict = {}`) | The classic bug is a default that *accumulates caller data* and leaks it between calls. Here the dict is a memo whose value is a pure function of its key: `start` depends only on `(index, size_s)`, so a hit and a cold computation are indistinguishable. It is bounded (`len(_cache) >= _BUCKET_CACHE_MAX` → `clear()` before insert, so the size never exceeds 1024 — not an unbounded-growth leak), it is documented as deliberate, and the leading underscore marks it private. `check_bucket_memo` drives the cache three times past its bound and asserts every answer still equals the cold-cache answer. |
| 2 | 33, 38 | `//` and `%` on a value that can go negative (replayed pre-cut-over events) | Python's floor division and modulo are consistent for negative operands: `a == size*(a//size) + a%size` always, and `a % size` is non-negative for positive `size`. So `index` and `start` agree for timestamps before `WINDOW_ORIGIN` — the case a reviewer expects to break. `check_bucket_spec` asserts the *spec* (`start <= ts < start + size` and `(start - ORIGIN) % size == 0`) over 400+ timestamps straddling the origin at five window sizes, rather than re-implementing the formula. |
| 3 | 55–63 | swallowed exception (`except (...): rejected.append(raw); continue`) | The module docstring and the function docstring state the contract: the gateway is a public endpoint, a malformed event must not abort a batch, and the caller ships `rejected` to the dead-letter queue. Nothing is *silently* dropped — every rejected event is handed back, which is the exact difference from B4's planted swallow (which appends nothing). The caught exception types are narrow (`KeyError, TypeError, ValueError`), not bare `except:`. |
| 4 | 76–84 | double-checked locking / racy read outside the lock | This is the safe form. The unlocked `self._counters.get(tenant)` is a fast path only; the re-check *inside* the lock is what decides whether to insert, so exactly one counter object can ever be created per tenant. A dict lookup is atomic, and a counter, once inserted, is never replaced — so a fast-path hit can never return a stale or half-built object. Contrast B3, where the value read outside the lock is *written back* — that one is a real lost update. `check_concurrent_record` runs 16 threads × 250 records through a barrier and asserts one counter object and zero lost units. |
| 5 | 86–93 | the same read-modify-write shape as B3's bug | Here the read *and* the write are both inside `with self._lock`, which is what makes it correct. Deliberately shaped like the planted race so that a model flagging it is demonstrably pattern-matching. |
| 6 | 107–113 | mutating a dict while iterating it (`del` inside a `for`) | Both loops iterate over `list(...)` snapshots taken before the deletions, which is the standard, documented way to delete during iteration. The whole method holds the lock, so no other thread can mutate concurrently either. `check_prune` exercises it and asserts the exact kept/dropped sets. |
| 7 | 118–123 | off-by-one / the `[-0:]` trap in a tail slice | `ordered[-n:]` returns the *whole* list when `n == 0`, which would be a real bug — and that is exactly why the `if n <= 0: return []` guard is there. The guard looks like defensive noise; it is load-bearing. `n > len(ordered)` returning everything is the documented behaviour ("the n most recent"). |
| 8 | 126–128 | off-by-one in `range(1, len(totals))` | A window-over-window difference series has `len(totals) - 1` elements by definition; starting at index 1 and reading `i-1` is correct and never indexes out of range. Empty input and a single bucket both yield `[]`, asserted explicitly. |
| 9 | 131–135 | float-free rounding via a magic `+ 500` | `(units * rate + 500) // 1000` is exact half-up rounding on integers — the intended behaviour for money, and stricter than `round()`, which is banker's rounding (`round(2.5) == 2`). No float is ever constructed. `check_billable_cents` compares against a `Decimal` `ROUND_HALF_UP` reference over 500 pseudo-random pairs plus the half-way edge cases. Negative inputs raise `ValueError` rather than rounding oddly. |
| 10 | 138–146 | timezone handling; a "day" that is not 24 hours | The epoch is decoded as UTC and then converted to the tenant's zone with `ZoneInfo`, so the calendar-day key follows local midnight, including the 23-hour and 25-hour DST days. The docstring states that this is intended: the billing unit is the calendar day, not a fixed 24-hour span. Constructing `ZoneInfo` per call is a performance nit, not a defect. `check_local_day_key` pins both 2026 European transitions and a southern-hemisphere zone. |

## Deliberate non-defects a reviewer may still raise

- **`bucket_start` does not validate `size_s > 0`.** A caller passing `0` gets a
  `ZeroDivisionError`. It is an internal helper with a documented precondition;
  no caller in the module can pass `0`. Missing input validation on a private
  helper is a robustness preference, not a defect.
- **`Meter._counters` is exposed without a property.** Underscore-private; the
  public read path (`snapshot`) copies under the lock.
- **`parse_events` mutates its `rejected` argument.** That is the documented
  out-parameter contract (identical in shape to B1/B2-era code and to B4's
  `errors`), and the caller owns the list.

## Verification

```
uv run eval/tasks/B_review/B6_control_nobugs/grade/verify_bugs.py
# 8/8 PASS -> "CONTROL VERIFIED: no defect in src/rate_window.py"
```
