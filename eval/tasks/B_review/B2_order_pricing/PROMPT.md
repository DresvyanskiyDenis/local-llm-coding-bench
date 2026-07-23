# Task: code review — tiered order pricing

Review `src/pricing.py`. It contains **three real bugs**. Find them.

For each bug you find, report it as a JSON object with exactly these keys:
- `"file"` — the file path (e.g. `"src/pricing.py"`)
- `"line"` — the line number of the bug (an int; if the bug spans several
  lines, use the line you consider most representative)
- `"description"` — a short, specific description of what's wrong

Output your findings as a **single fenced code block labeled `json`**
containing a JSON array of these objects, and nothing else inside that
block. You may add prose analysis before or after the block, but the block
itself must be valid, parseable JSON. Example format:

```json
[
  {"file": "src/pricing.py", "line": 20, "description": "comparison operator is backwards"}
]
```

Do not modify any files — this is a read-only review. Just report your
findings in the format above.
