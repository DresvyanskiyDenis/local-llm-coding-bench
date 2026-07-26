"""Reference solution for C4_already_done (audit only, not shipped to the model).

Fixes review comments 1-2; deliberately does NOT act on comment 3 (the
noise comment) -- clamp_hours already guards against negative hours, so
there is nothing to add.
"""

from __future__ import annotations


def calculate_overtime_pay(hours_worked: float, hourly_rate: float) -> float:
    """Hours up to 40 are paid at hourly_rate; hours beyond 40 are paid at
    1.5x hourly_rate (time-and-a-half). Return the total pay for the week."""
    if hours_worked <= 40:
        return hours_worked * hourly_rate
    regular = 40 * hourly_rate
    overtime = (hours_worked - 40) * hourly_rate * 1.5
    return regular + overtime


def round_to_nearest_cent(amount: float) -> float:
    """Round a dollar amount to the nearest cent (standard rounding, not
    truncation)."""
    return round(amount, 2)


def clamp_hours(hours_worked: float, max_hours: float = 60.0) -> float:
    """Clamp reported hours to [0, max_hours] -- payroll data entry
    sometimes contains negative or absurdly large typos and this guards
    against them."""
    if hours_worked < 0:
        return 0.0
    if hours_worked > max_hours:
        return max_hours
    return hours_worked
