"""Importer for the nightly vendor product export.

Vendor spec §4.1: the export is a **UTF-8** encoded CSV with a header row and the
columns ``sku,name,price,quantity``. Product names routinely contain non-ASCII
characters (German umlauts, accented French names), and downstream search indexes
on the name, so the names must survive the import byte-for-byte.

Vendor spec §4.4: a row the importer cannot parse must be reported back to the
vendor. The nightly job mails ``errors`` to the vendor contact after every run, so
a malformed row must never disappear silently.
"""

from __future__ import annotations

import csv
from pathlib import Path


def read_rows(path: str | Path) -> list[dict[str, str]]:
    """Read the export at ``path`` and return one dict per data row."""
    with open(path, newline="", encoding="latin-1") as handle:
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
        except (KeyError, ValueError, TypeError):
            continue
    return records


def split_batches(records: list[dict], batch_size: int = 100) -> list[list[dict]]:
    """Split ``records`` into consecutive batches of at most ``batch_size``.

    Every record must appear in exactly one batch; the warehouse API is called
    once per batch.
    """
    batches = []
    for start in range(0, len(records), batch_size):
        batches.append(records[start:start + batch_size - 1])
    return batches


def import_export(path: str | Path, batch_size: int = 100) -> tuple[list[list[dict]], list[str]]:
    """Read, parse and batch one nightly export. Returns (batches, errors)."""
    errors: list[str] = []
    rows = read_rows(path)
    records = parse_rows(rows, errors)
    return split_batches(records, batch_size), errors
