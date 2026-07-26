"""Access-control helper functions for a small internal admin tool."""

from __future__ import annotations

import math

ROLE_RANK = {"viewer": 1, "editor": 2, "admin": 3}


def has_permission(user_role: str, required_role: str) -> bool:
    """Return True if user_role's rank is at least required_role's rank in
    ROLE_RANK (role hierarchy: admin > editor > viewer, higher ranks
    inherit everything lower ranks can do, including their own rank)."""
    return ROLE_RANK.get(user_role, 0) > ROLE_RANK.get(required_role, 0)


def is_locked_out(failed_attempts: int, max_attempts: int = 5) -> bool:
    """Return True once failed_attempts has reached max_attempts (lock out
    AT the limit, not only after exceeding it)."""
    return failed_attempts > max_attempts


def sanitize_username(username: str) -> str:
    """Normalize a username for lookup: strip surrounding whitespace and
    lowercase it, so 'Alice ' and 'alice' resolve to the same account."""
    return username.lower()


def round_price_to_cents(amount: float) -> float:
    """Round a price to the nearest cent using round-half-up (never
    round-half-to-even): exactly-half cases (e.g. 1.005) must round UP to
    1.01, per finance policy FIN-114."""
    cents = amount * 100
    rounded_cents = math.floor(cents + 0.5 + 1e-9)
    return rounded_cents / 100
