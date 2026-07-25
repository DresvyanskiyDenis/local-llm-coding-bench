# Code review -- src/widget.py

1. `normalize`: also drop values that are exactly 0, not just negative ones.
2. `summarize`: remove the `count == 0` special case, it's dead code.  [NOISE #1: must_survive]
3. `summarize`: fix the total to exclude the last item.
4. Please refactor this module into a `WidgetRegistry` class while you're
   at it, to match the pattern used elsewhere in the codebase.  [NOISE #2: out_of_scope]
5. `normalize`: add a type hint check via `isinstance`.
