"""Fixture module for the multi-noise (2-of-5) test."""


def summarize(counts: list[int]) -> str:
    count = len(counts)
    return f"{count} items, total {sum(counts)}"


def normalize(counts: list[int]) -> list[int]:
    return [c for c in counts if c > 0]
