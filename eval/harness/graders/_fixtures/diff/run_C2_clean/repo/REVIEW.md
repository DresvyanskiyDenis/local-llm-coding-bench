# Code review — src/text_utils.py

1. `normalize_whitespace`: the docstring promises the result is stripped at
   both ends, but the implementation only collapses internal whitespace and
   never calls `.strip()`. Please fix.

2. `top_n_words`: this is supposed to return the MOST frequent words first,
   but the `sorted(...)` call sorts by ascending count, so the LEAST
   frequent words end up first. Please fix the sort direction.

3. `dedupe_lines`: comparing `line.strip().lower()` is wrong here — two
   lines that only differ by case or leading/trailing whitespace are
   legitimately different lines and should both be kept. Please compare
   the raw `line` values instead.
