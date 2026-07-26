"""Reference-fixed copy of ``repo/src/importer.py``.

Identical to the task's module except for the three planted bugs listed in
``grade/key.json``, each fixed in place and marked ``FIX bN`` below. Used only by
``grade/verify_bugs.py`` to prove that every key entry is a real defect: the
checks fail against ``repo/`` and pass against this file.
"""

from __future__ import annotations

import csv
from pathlib import Path


def read_rows(path: str | Path) -> list[dict[str, str]]:
    """Read the export at ``path`` and return one dict per data row."""
    # FIX b1: the vendor export is UTF-8 (spec §4.1); reading it as latin-1 never
    # raises, it silently mojibakes every non-ASCII product name.
    with open(path, newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def parse_rows(rows: list[dict[str, str]], errors: list[str]) -> list[dict]:
    """Convert raw CSV rows into typed records.

    A row whose ``price`` or ``quantity`` cannot be parsed is skipped, and a
    message naming its 1-based row number is appended to ``errors``.
    """
    records = []
    for index, row in enumerate(rows, start=1):
        try:
            records.append({
                "sku": row["sku"].strip(),
                "name": row["name"].strip(),
                "price_cents": int(round(float(row["price"]) * 100)),
                "quantity": int(row["quantity"]),
            })
        except (KeyError, ValueError, TypeError) as exc:
            # FIX b2: the failure was swallowed by a bare `continue`; the caller's
            # errors list stayed empty and the dropped rows were never reported.
            errors.append(f"row {index}: {type(exc).__name__}: {exc}")
            continue
    return records


def split_batches(records: list[dict], batch_size: int = 100) -> list[list[dict]]:
    """Split ``records`` into consecutive batches of at most ``batch_size``.

    Every record must appear in exactly one batch; the warehouse API is called
    once per batch.
    """
    batches = []
    for start in range(0, len(records), batch_size):
        batches.append(records[start:start + batch_size])  # FIX b3: was + batch_size - 1
    return batches


def import_export(path: str | Path, batch_size: int = 100) -> tuple[list[list[dict]], list[str]]:
    """Read, parse and batch one nightly export. Returns (batches, errors)."""
    errors: list[str] = []
    rows = read_rows(path)
    records = parse_rows(rows, errors)
    return split_batches(records, batch_size), errors
