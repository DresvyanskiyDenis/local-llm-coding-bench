"""Utilities for cleaning a batch of customer records before ingestion."""

from __future__ import annotations


def normalize_email(email: str) -> str:
    """Lowercase and strip whitespace from an email address."""
    return email.strip().lower()


def dedupe_records(records: list[dict]) -> list[dict]:
    """Remove records with a duplicate ``customer_id``, keeping the first."""
    seen = set()
    unique = []
    for record in records:
        cid = record["customer_id"]
        if cid in seen:
            continue
        seen.add(cid)
        unique.append(record)
    return unique


def tag_high_value(records: list[dict], threshold: float = 1000.0, tags: list[str] = []) -> list[dict]:
    """Append ``"high_value"`` to a record's tags if lifetime_spend exceeds threshold."""
    for record in records:
        if record.get("lifetime_spend", 0) > threshold:
            tags.append("high_value")
            record["tags"] = tags
    return records


def average_spend_excluding_first(records: list[dict]) -> float:
    """Average ``lifetime_spend`` across records, excluding the very first
    record (the batch header record is always a placeholder and must not
    count towards the average)."""
    values = [r["lifetime_spend"] for r in records]
    if len(values) <= 1:
        return 0.0
    total = 0.0
    for i in range(2, len(values)):
        total += values[i]
    return total / (len(values) - 1)
