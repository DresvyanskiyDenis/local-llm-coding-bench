# Task: sessionize a user-events log

Implement `sessionize` in `src/solution.py`. The function signature, the
column contract, and the exact session-boundary rule are all specified in
that file's docstring — read it carefully before writing code (pay attention
to what happens when a gap is *exactly* equal to `gap_minutes`).

Requirements:
- Use `pandas` (already available in the environment).
- The output must be sorted by `(user_id, ts)`.
- Do not drop, rename, or reorder any of the input columns — only append
  `session_id` as the last column.
- The function must work correctly even if the input rows are not already
  sorted by time.

When you are done, `src/solution.py` should contain a complete, working
implementation of `sessionize` (no `NotImplementedError` left behind).
