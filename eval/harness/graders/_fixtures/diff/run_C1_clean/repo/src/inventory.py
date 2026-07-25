"""Inventory stock-level helpers."""

from __future__ import annotations


def restock_needed(current_stock: int, reorder_point: int) -> bool:
    """Return True if stock is at or below the reorder point."""
    return current_stock <= reorder_point


def apply_restock(current_stock: int, incoming: int) -> int:
    """Add incoming units to current stock."""
    return current_stock + incoming


def days_of_supply(current_stock: int, daily_usage: float) -> float:
    """Estimate how many days current stock will last.

    A daily_usage of 0 means the item isn't being consumed, so supply is
    treated as effectively infinite.
    """
    if daily_usage == 0:
        return float("inf")
    return current_stock / daily_usage


def low_stock_items(items: dict[str, int], reorder_point: int) -> list[str]:
    """Return names of items whose stock is at/below the reorder point, sorted."""
    result = []
    for name, stock in items.items():
        if stock <= reorder_point:
            result.append(name)
    return sorted(result)
