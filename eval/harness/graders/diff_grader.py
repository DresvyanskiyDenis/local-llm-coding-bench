# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""diff_grader.py — surgical-edit-discipline verdict for C_edit (pairs with pytest_grader),
per CONTRACT.md §2.

Uses difflib (task repos are plain copied trees, not git repos) to diff the task's
original tasks/<suite>/<id>/repo/ against the model's edited <rundir>/repo/.
`touched_expected_only` is checked against meta.json's `entrypoint` (str or list); null if
meta.json declares no entrypoint (can't know what was "expected"). `noise_comment_acted_on`
is checked against an optional grade/noise.json {"file", and ONE of:
"forbidden_pattern" (regex) | "forbidden_snippet" (literal) -> acted-on == PRESENT, for a
noise comment that would ADD bad code; OR "required_pattern" (regex) | "required_snippet"
(literal) -> acted-on == ABSENT, for a noise comment that would REMOVE/alter correct code
that must survive}. Both C_edit noise comments here are the remove-correct-code kind, so they
use required_*. CONTRACT's "documented in grade/meta" doesn't fix an exact shape, so this is
the convention this grader expects; null if that file doesn't exist (not a C_edit task, or
Component 1 hasn't written one). surgical_score is a heuristic (no
reference diff size is provided by the task): 1.0 minus a penalty for unexpected files
touched and for changed lines beyond a small free allowance, minus 0.3 per noise entry that
was wrongly acted on.

Round 2: noise.json grows a `kind` field -- "out_of_scope" | "already_done" |
"contradiction" | "must_survive" -- and may carry MULTIPLE entries (a `{"noise": [...]}`
list, for tasks with e.g. 2 noise comments out of 5). Backward compatibility is strict:
a noise.json that is a single object with NO "kind" key (today's only shape, e.g. C1/C2)
is graded through the exact old code path and produces the exact old verdict shape
(bare `noise_comment_acted_on`, no extra keys) -- untouched, unextended, byte-identical.
Only a noise.json that opts into the new schema (has a "kind" key, and/or the
`{"noise": [...]}` list wrapper) gets the extended verdict: the top-level
`noise_comment_acted_on` becomes an aggregate (true if ANY entry was acted on, for
existing consumers), plus a new `noise` list with one entry per noise comment.

`kind` -> which grade/noise.json key it pairs with (the diff-checkable kinds reuse the
existing forbidden_*/required_* machinery, just directed by `kind`):
  - "must_survive"  (today's only kind, now explicit) -> required_pattern/required_snippet:
    correct code that must remain untouched; acted_on == it is now ABSENT.
  - "already_done"  -> required_pattern/required_snippet: the already-correct
    implementation must remain untouched; acted_on == it is now ABSENT (the model
    redundantly "fixed" something that needed no fix).
  - "out_of_scope"  -> forbidden_pattern/forbidden_snippet: the out-of-scope refactor
    must NOT appear; acted_on == it is now PRESENT.
  - "contradiction" -> NOT diff-gradable (see below); no forbidden_*/required_* is
    consulted for this kind, and its per-entry `acted_on` is always `null`.

"contradiction" is the one noise kind a diff cannot grade: the question is whether the
model SURFACED the conflict between two contradicting review comments, which lives in
prose (<rundir>/answer.txt), not in the tree. For kind == "contradiction" this grader
instead reads answer.txt and reports `conflict_surfaced: true|false|null` (null if
answer.txt is missing) via a case-insensitive substring match against
`conflict_signal.answer_must_mention` (true if ANY listed phrase appears). This is
reported honestly as `conflict_signal_kind: "keyword_match"` -- a WEAKER signal than the
diff-based checks above, and it must never be presented as equivalent to them.

Usage:
    uv run diff_grader.py --task tasks/C_edit/C1_... \\
        --run runs/qwen__q5__C_edit__C1__rep1 --out runs/.../grade_diff.json
"""

import argparse
import difflib
import json
import re
from pathlib import Path

FREE_LINES = 15  # changed lines a small task-sized edit shouldn't need to exceed


def _check_pattern_field(noise, text):
    """Today's exact forbidden_*/required_* -> acted_on logic, applied to one noise
    entry's fields against one file's text. Returns None if the entry declares none of
    the four recognised fields (nothing to check)."""
    if noise.get("forbidden_pattern"):  # acted-on = bad code was ADDED
        return bool(re.search(noise["forbidden_pattern"], text, re.I))
    if noise.get("forbidden_snippet"):
        return noise["forbidden_snippet"].lower() in text.lower()
    if noise.get("required_pattern"):  # acted-on = correct code was REMOVED/altered
        return not re.search(noise["required_pattern"], text, re.I)
    if noise.get("required_snippet"):
        return noise["required_snippet"].lower() not in text.lower()
    return None


def _grade_noise_entry(noise, new_root, run_dir):
    """Grade one noise.json entry (dict) against the edited repo / answer.txt. Returns a
    verdict dict for the `noise` list; `kind` defaults to "must_survive" (today's only,
    now-explicit kind) when absent."""
    kind = noise.get("kind", "must_survive")
    entry = {"kind": kind, "file": noise.get("file")}

    if kind == "contradiction":
        signal = (noise.get("conflict_signal") or {}).get("answer_must_mention", [])
        answer_path = run_dir / "answer.txt"
        if answer_path.exists():
            answer_text = answer_path.read_text(errors="replace").lower()
            entry["conflict_surfaced"] = any(s.lower() in answer_text for s in signal)
        else:
            entry["conflict_surfaced"] = None
        entry["conflict_signal_kind"] = "keyword_match"
        entry["acted_on"] = None  # not diff-gradable, per the module docstring
        return entry

    target = new_root / noise.get("file", "")
    acted_on = None
    if noise.get("file") and target.exists():
        acted_on = _check_pattern_field(noise, target.read_text(errors="replace"))
    entry["acted_on"] = acted_on
    return entry


def read_tree(root):
    files = {}
    for p in root.rglob("*"):
        if p.is_file():
            rel = p.relative_to(root).as_posix()
            try:
                files[rel] = p.read_text(errors="replace").splitlines(keepends=True)
            except Exception:
                files[rel] = None  # binary/unreadable -> whole-file add/remove count only
    return files


def diff_trees(orig_root, new_root):
    orig, new = read_tree(orig_root), read_tree(new_root)
    touched = []
    added_total = removed_total = 0
    for rel in sorted(set(orig) | set(new)):
        o_lines, n_lines = orig.get(rel), new.get(rel)
        if o_lines == n_lines:
            continue
        touched.append(rel)
        if o_lines is None or n_lines is None:
            if rel not in orig:
                added_total += len(n_lines or [])
            elif rel not in new:
                removed_total += len(o_lines or [])
            continue
        for line in difflib.unified_diff(o_lines, n_lines, lineterm=""):
            if line.startswith("+++") or line.startswith("---"):
                continue
            if line.startswith("+"):
                added_total += 1
            elif line.startswith("-"):
                removed_total += 1
    return touched, added_total, removed_total


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--task", required=True)
    ap.add_argument("--run", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    task_dir = Path(args.task)
    run_dir = Path(args.run)
    orig_root = task_dir / "repo"
    new_root = run_dir / "repo"

    touched, added_total, removed_total = diff_trees(orig_root, new_root)

    meta = json.loads((task_dir / "meta.json").read_text())
    entry = meta.get("entrypoint")
    expected = {entry} if isinstance(entry, str) else set(entry) if isinstance(entry, list) else set()
    touched_expected_only = all(t in expected for t in touched) if expected else None

    noise_acted_on = None
    noise_entries_out = None  # only populated when noise.json opts into the round-2 schema
    noise_path = task_dir / "grade" / "noise.json"
    if noise_path.exists():
        raw = json.loads(noise_path.read_text())
        # New schema opt-in: either the {"noise": [...]} list wrapper, or a single object
        # that carries a "kind" key. Anything else is today's exact single-object,
        # untagged shape and MUST stay on the old code path below, unmodified, so its
        # verdict is byte-identical to before this change.
        if isinstance(raw, dict) and "noise" in raw:
            entries_in = raw["noise"]
            noise_entries_out = [_grade_noise_entry(n, new_root, run_dir) for n in entries_in]
        elif isinstance(raw, dict) and "kind" in raw:
            noise_entries_out = [_grade_noise_entry(raw, new_root, run_dir)]
        else:
            noise = raw if isinstance(raw, dict) else {}
            target = new_root / noise.get("file", "")
            if noise.get("file") and target.exists():
                noise_acted_on = _check_pattern_field(noise, target.read_text(errors="replace"))

        if noise_entries_out is not None:
            flags = [e["acted_on"] for e in noise_entries_out]
            if any(f is True for f in flags):
                noise_acted_on = True
            elif any(f is False for f in flags):
                noise_acted_on = False
            else:
                noise_acted_on = None  # every entry was e.g. "contradiction" (not diff-gradable)

    noise_true_count = (
        sum(1 for e in noise_entries_out if e["acted_on"] is True) if noise_entries_out is not None
        else (1 if noise_acted_on else 0)
    )

    changed_lines = added_total + removed_total
    score = 1.0
    if expected and not touched_expected_only:
        extra = len(set(touched) - expected)
        score -= min(0.5, extra * 0.15)
    if changed_lines > FREE_LINES:
        score -= min(0.4, (changed_lines - FREE_LINES) * 0.02)
    score -= 0.3 * noise_true_count  # same 0.3 penalty as before per acted-on noise entry
    surgical_score = round(max(0.0, min(1.0, score)), 3)

    verdict = {
        "grader": "diff",
        "files_touched": len(touched), "lines_added": added_total, "lines_removed": removed_total,
        "touched_expected_only": touched_expected_only,
        "noise_comment_acted_on": noise_acted_on,
        "surgical_score": surgical_score,
    }
    if noise_entries_out is not None:
        verdict["noise"] = noise_entries_out
    Path(args.out).write_text(json.dumps(verdict, indent=2))
    print(json.dumps(verdict, indent=2))


if __name__ == "__main__":
    main()
