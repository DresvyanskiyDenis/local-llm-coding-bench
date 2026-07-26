# Code review — src/shipping.py

1. `calculate_shipping_cost`: the docstring promises a $3.00 fragile-handling
   surcharge, but the implementation never adds it. Please add the surcharge
   when `package.fragile` is True.

2. `apply_bulk_discount`: the docstring says the discount applies at "5 or
   more" packages, but the comparison uses `> 5`, which excludes exactly 5.
   Off-by-one — should be `>= 5`.

3. `estimate_delivery_days`: the docstring says the day count should round
   UP (ceiling), but `//` is floor division, so e.g. 600km comes out to 1
   day instead of 2. Please use ceiling division instead.

4. While you're in this file: `Package` is a plain class with a hand-written
   `__init__` — the whole module would be cleaner and more consistent with
   our other models if `Package` (and any other plain data-holder classes we
   add here later) used `@dataclass` instead. Please convert `Package` to a
   dataclass while you're at it.
