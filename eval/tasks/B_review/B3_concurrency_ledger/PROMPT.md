# Task: code review — concurrent settlement ledger

Review `src/ledger.py`. It contains **three real bugs**. Find them.

For each bug you find, report it as a JSON object with exactly these keys:
- `"file"` — the file path (e.g. `"src/ledger.py"`)
- `"line"` — the line number of the bug (an int; if the bug spans several
  lines, use the line you consider most representative)
- `"description"` — a short, specific description of what's wrong

Output your findings as a **single fenced code block labeled `json`**
containing a JSON array of these objects, and nothing else inside that
block. You may add prose analysis before or after the block, but the block
itself must be valid, parseable JSON. Example format:

```json
[
  {"file": "src/ledger.py", "line": 12, "description": "off-by-one: loop skips the last element"}
]
```

Do not modify any files — this is a read-only review. Just report your
findings in the format above.
