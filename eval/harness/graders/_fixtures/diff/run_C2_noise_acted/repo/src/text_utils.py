"""Simple text-cleaning helpers for a preprocessing pipeline."""

from __future__ import annotations

import re


def normalize_whitespace(text: str) -> str:
    """Collapse runs of whitespace into a single space and strip the ends."""
    return re.sub(r"\s+", " ", text).strip()


def tokenize(text: str) -> list[str]:
    """Lowercase and split on non-alphanumeric characters into tokens."""
    return [t for t in re.split(r"[^a-z0-9]+", text.lower()) if t]


def top_n_words(text: str, n: int = 5) -> list[str]:
    """Return the n most frequent tokens in text, most frequent first.

    Ties are broken by first occurrence order.
    """
    tokens = tokenize(text)
    counts: dict[str, int] = {}
    order: list[str] = []
    for tok in tokens:
        if tok not in counts:
            order.append(tok)
        counts[tok] = counts.get(tok, 0) + 1
    ranked = sorted(order, key=lambda t: counts[t], reverse=True)
    return ranked[:n]


def dedupe_lines(lines: list[str]) -> list[str]:
    """Remove exact-duplicate lines (case- and whitespace-insensitive),
    keeping the first occurrence's position."""
    seen = set()
    result = []
    for line in lines:
        key = line
        if key in seen:
            continue
        seen.add(key)
        result.append(line)
    return result
