# Task: implement a schema record validator

Implement `validate_record` in `src/solution.py`. The exact schema format,
the exact error-message strings, and several tricky edge cases (booleans vs.
ints, error ordering, suppressing redundant errors) are all specified in
that file's docstring — read it carefully before writing code.

Requirements:
- Pure Python, no third-party dependencies.
- Error messages must match the specified format **exactly** (they are
  compared as literal strings).
- Errors must be returned in schema-iteration order.

When you are done, `src/solution.py` should contain a complete, working
implementation of `validate_record` (no `NotImplementedError` left behind).
