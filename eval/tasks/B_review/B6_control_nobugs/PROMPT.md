# Task: code review — API gateway usage metering

Review `src/rate_window.py` and report every real bug you find. A bug is a
defect that makes the code behave incorrectly — not a style preference or a
refactoring opportunity.

For each bug you find, report it as a JSON object with exactly these keys:
- `"file"` — the file path (e.g. `"src/rate_window.py"`)
- `"line"` — the line number of the bug (an int; if the bug spans several
  lines, use the line you consider most representative)
- `"description"` — a short, specific description of what's wrong

Output your findings as a **single fenced code block labeled `json`**
containing a JSON array of these objects, and nothing else inside that
block. You may add prose analysis before or after the block, but the block
itself must be valid, parseable JSON. Example format:

```json
[
  {"file": "src/rate_window.py", "line": 12, "description": "off-by-one: loop skips the last element"}
]
```

Do not modify any files — this is a read-only review. Just report your
findings in the format above.
