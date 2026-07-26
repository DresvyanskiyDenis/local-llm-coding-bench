"""Reference solution for C5_contradiction (audit only, not shipped to the model).

Fixes review comments 1-3; deliberately does NOT act on comments 4 or 5
(both target round_price_to_cents and directly contradict each other --
comment 4 asks to replace the half-up logic with round() (round-half-to-
even), comment 5 insists halves must always round up. The existing
math.floor(cents + 0.5) implementation already satisfies comment 5 and
would be broken by comment 4, so the correct response is to leave it
untouched and flag the contradiction rather than silently pick a side).
"""

from __future__ import annotations

import math

ROLE_RANK = {"viewer": 1, "editor": 2, "admin": 3}


def has_permission(user_role: str, required_role: str) -> bool:
    """Return True if user_role's rank is at least required_role's rank in
    ROLE_RANK (role hierarchy: admin > editor > viewer, higher ranks
    inherit everything lower ranks can do, including their own rank)."""
    return ROLE_RANK.get(user_role, 0) >= ROLE_RANK.get(required_role, 0)


def is_locked_out(failed_attempts: int, max_attempts: int = 5) -> bool:
    """Return True once failed_attempts has reached max_attempts (lock out
    AT the limit, not only after exceeding it)."""
    return failed_attempts >= max_attempts


def sanitize_username(username: str) -> str:
    """Normalize a username for lookup: strip surrounding whitespace and
    lowercase it, so 'Alice ' and 'alice' resolve to the same account."""
    return username.strip().lower()


def round_price_to_cents(amount: float) -> float:
    """Round a price to the nearest cent using round-half-up (never
    round-half-to-even): exactly-half cases (e.g. 1.005) must round UP to
    1.01, per finance policy FIN-114."""
    cents = amount * 100
    rounded_cents = math.floor(cents + 0.5 + 1e-9)
    return rounded_cents / 100
