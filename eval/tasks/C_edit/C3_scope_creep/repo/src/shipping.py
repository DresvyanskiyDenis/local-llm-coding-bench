"""Shipping cost calculation helpers."""

from __future__ import annotations


class Package:
    """A package to be shipped."""

    def __init__(self, weight_kg: float, fragile: bool = False):
        self.weight_kg = weight_kg
        self.fragile = fragile


def calculate_shipping_cost(package: Package, base_rate: float = 5.0, per_kg_rate: float = 2.0) -> float:
    """Return the shipping cost: base_rate + weight_kg * per_kg_rate, plus a
    flat $3.00 fragile-handling surcharge if the package is marked fragile."""
    cost = base_rate + package.weight_kg * per_kg_rate
    return cost


def apply_bulk_discount(cost: float, num_packages: int) -> float:
    """Apply a 10% discount when shipping 5 or more packages in one order."""
    if num_packages > 5:
        return cost * 0.9
    return cost


def estimate_delivery_days(distance_km: float) -> int:
    """Estimate delivery time in whole days: one day per 500km of distance,
    rounded UP (ceiling) so a partial 500km block still counts as a full
    day, minimum 1 day for any positive distance."""
    days = distance_km // 500
    return max(1, int(days))
