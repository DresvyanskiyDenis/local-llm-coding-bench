"""Sliding-window usage metering for the API gateway.

Every gateway node ships raw events ``{"tenant": str, "ts": epoch_seconds,
"units": int}`` into this module. Events are bucketed into fixed windows anchored
on ``WINDOW_ORIGIN`` (the epoch second the metering cut-over happened), counted
per tenant, pruned as they age out, and finally priced in whole cents.

Two invariants the rest of the billing stack depends on:

* Money is integer cents end to end. No float ever touches a money value.
* Replayed events are legal. The gateway retries batches after an outage, so an
  event whose timestamp is *before* ``WINDOW_ORIGIN`` must land in the window it
  belongs to rather than being clamped or dropped.
"""

from __future__ import annotations

import threading
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

WINDOW_ORIGIN = 1_600_000_000  # 2020-09-13T12:26:40Z, the metering cut-over second
_BUCKET_CACHE_MAX = 1024


def bucket_start(epoch_s: int, size_s: int = 60, _cache: dict = {}) -> int:
    """Start second of the fixed window ``epoch_s`` falls into (``size_s`` > 0).

    ``_cache`` is a deliberate module-lifetime memo, not an accident: this is the
    hot path (once per event) and the result is a pure function of the cache key.
    It is bounded by ``_BUCKET_CACHE_MAX``.
    """
    index = (epoch_s - WINDOW_ORIGIN) // size_s
    key = (index, size_s)
    cached = _cache.get(key)
    if cached is not None:
        return cached
    start = epoch_s - (epoch_s - WINDOW_ORIGIN) % size_s
    if len(_cache) >= _BUCKET_CACHE_MAX:
        _cache.clear()
    _cache[key] = start
    return start


def parse_events(raw_events, rejected: list) -> list[tuple[str, int, int]]:
    """Normalise raw gateway events into ``(tenant, epoch_s, units)`` triples.

    The gateway is a public endpoint, so a malformed event must never abort a
    batch: it is appended to ``rejected`` and skipped, and the caller ships
    ``rejected`` to the dead-letter queue.
    """
    events = []
    for raw in raw_events:
        try:
            tenant = str(raw["tenant"]).strip()
            epoch_s = int(raw["ts"])
            units = int(raw["units"])
        except (KeyError, TypeError, ValueError):
            rejected.append(raw)
            continue
        if not tenant or units < 0:
            rejected.append(raw)
            continue
        events.append((tenant, epoch_s, units))
    return events


class Meter:
    """Per-tenant window counters. Every method is safe to call concurrently."""

    def __init__(self, size_s: int = 60) -> None:
        self._size_s = size_s
        self._lock = threading.Lock()
        self._counters: dict[str, dict[int, int]] = {}

    def _counter_for(self, tenant: str) -> dict[int, int]:
        counter = self._counters.get(tenant)
        if counter is None:
            with self._lock:
                counter = self._counters.get(tenant)
                if counter is None:
                    counter = {}
                    self._counters[tenant] = counter
        return counter

    def record(self, tenant: str, epoch_s: int, units: int) -> int:
        """Add ``units`` to the tenant's window for ``epoch_s``; return its total."""
        counter = self._counter_for(tenant)
        start = bucket_start(epoch_s, self._size_s)
        with self._lock:
            total = counter.get(start, 0) + units
            counter[start] = total
        return total

    def snapshot(self, tenant: str) -> dict[int, int]:
        """A copy of one tenant's buckets, safe to read outside the lock."""
        with self._lock:
            return dict(self._counters.get(tenant, {}))

    def prune(self, now_s: int, keep_windows: int = 5) -> int:
        """Drop every bucket starting more than ``keep_windows`` windows before the
        one containing ``now_s``, and forget tenants left with no buckets. Returns
        the number of buckets dropped."""
        cutoff = bucket_start(now_s, self._size_s) - keep_windows * self._size_s
        dropped = 0
        with self._lock:
            for tenant in list(self._counters):
                counter = self._counters[tenant]
                for start in list(counter):
                    if start < cutoff:
                        del counter[start]
                        dropped += 1
                if not counter:
                    del self._counters[tenant]
        return dropped


def recent_totals(buckets: dict[int, int], n: int) -> list[int]:
    """Totals of the ``n`` most recent buckets of a snapshot, oldest first."""
    if n <= 0:
        return []
    ordered = [buckets[start] for start in sorted(buckets)]
    return ordered[-n:]


def deltas(totals: list[int]) -> list[int]:
    """Window-over-window changes; ``len(totals) - 1`` values, empty for one bucket."""
    return [totals[i] - totals[i - 1] for i in range(1, len(totals))]


def billable_cents(units: int, rate_cents_per_1k: int) -> int:
    """Cost of ``units`` units, rounded half-up to whole cents, integers only."""
    if units < 0 or rate_cents_per_1k < 0:
        raise ValueError("units and rate must be non-negative")
    return (units * rate_cents_per_1k + 500) // 1000


def local_day_key(epoch_s: int, tz_name: str) -> str:
    """The tenant's local calendar day for ``epoch_s``, as ``YYYY-MM-DD``.

    Invoices group by the tenant's *calendar* day, which is 23 or 25 hours long on
    a DST-transition day. That is intended: the calendar day is the billing unit,
    not a fixed 24-hour span.
    """
    moment = datetime.fromtimestamp(epoch_s, tz=timezone.utc)
    return moment.astimezone(ZoneInfo(tz_name)).date().isoformat()
