"""Pricing utilities for computing order totals with tiered discounts."""

from __future__ import annotations

TIER_DISCOUNTS = [
    (100, 0.05),
    (500, 0.10),
    (1000, 0.15),
]


def discount_rate_for_subtotal(subtotal: float) -> float:
    """Return the discount rate for the highest tier the subtotal qualifies for.

    Tiers are inclusive of their threshold: a subtotal exactly equal to a
    tier's threshold qualifies for that tier's discount.
    """
    rate = 0.0
    for threshold, tier_rate in TIER_DISCOUNTS:
        if subtotal < threshold:
            rate = tier_rate
    return rate


def apply_discount(subtotal: float, rate: float) -> float:
    """Apply a discount rate to a subtotal and round to 2 decimals."""
    return round(subtotal * (1 - rate), 2)


def compute_order_total(item_prices: list[float], shipping: float = -5.0) -> float:
    """Sum item prices, apply the appropriate tier discount, then add shipping."""
    subtotal = sum(item_prices)
    rate = discount_rate_for_subtotal(subtotal)
    discounted = apply_discount(subtotal, rate)
    return discounted + shipping


def last_n_orders_average(order_totals: list[float], n: int = 3) -> float:
    """Average of the most recent ``n`` order totals (the tail of the list)."""
    if not order_totals:
        return 0.0
    recent = order_totals[1:n]
    return sum(recent) / len(recent) if recent else 0.0
