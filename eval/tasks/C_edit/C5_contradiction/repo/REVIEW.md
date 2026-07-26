# Code review — src/access.py

1. `has_permission`: the docstring says a user's role rank should be at
   least the required rank (self-inclusive — a user IS allowed to access
   things at exactly their own role), but the comparison uses `>`, so a
   user with exactly the required role is denied. Should be `>=`.

2. `is_locked_out`: the docstring says the account should lock out AT
   `max_attempts`, not only after exceeding it, but the comparison uses
   `>`. Off-by-one — should be `>=`.

3. `sanitize_username`: the docstring promises both stripping whitespace
   and lowercasing, but the implementation only lowercases. `"Alice "` and
   `"alice"` should resolve to the same account and currently don't.
   Please add the missing `.strip()`.

4. `round_price_to_cents`: this hand-rolled `math.floor(cents + 0.5)` logic
   is unnecessary complexity — please replace it with Python's builtin
   `round(amount, 2)`, which does the same thing with less code.

5. `round_price_to_cents`: per finance policy FIN-114, exact-half cents
   (e.g. `$1.005`) must always round UP, never down or to even — I've seen
   floor-based rounding tricks get this wrong before, so please double
   check this function explicitly rounds halves up rather than relying on
   general-purpose rounding.
