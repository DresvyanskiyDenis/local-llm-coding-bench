# Code review — src/inventory.py

1. `restock_needed`: the docstring says stock "at or below" the reorder
   point should trigger a restock, but the comparison uses `<` (strict).
   Off-by-one — should be `<=`.

2. `apply_restock`: this subtracts `incoming` from `current_stock`.
   Restocking should ADD the incoming units, not remove them. Please fix
   the arithmetic.

3. `low_stock_items`: the docstring promises the returned list is sorted,
   but the implementation returns items in dict-iteration order. Please
   sort the result before returning.

4. `days_of_supply`: returning `float("inf")` when `daily_usage` is 0 is
   confusing — please remove the zero-check entirely and let the division
   raise naturally. Callers should handle the exception themselves.
