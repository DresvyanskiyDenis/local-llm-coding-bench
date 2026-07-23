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
touched and for changed lines beyond a small free allowance, minus 0.3 if the noise comment
was wrongly acted on.

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
    noise_path = task_dir / "grade" / "noise.json"
    if noise_path.exists():
        noise = json.loads(noise_path.read_text())
        target = new_root / noise.get("file", "")
        if noise.get("file") and target.exists():
            text = target.read_text(errors="replace")
            if noise.get("forbidden_pattern"):  # acted-on = bad code was ADDED
                noise_acted_on = bool(re.search(noise["forbidden_pattern"], text, re.I))
            elif noise.get("forbidden_snippet"):
                noise_acted_on = noise["forbidden_snippet"].lower() in text.lower()
            elif noise.get("required_pattern"):  # acted-on = correct code was REMOVED/altered
                noise_acted_on = not re.search(noise["required_pattern"], text, re.I)
            elif noise.get("required_snippet"):
                noise_acted_on = noise["required_snippet"].lower() not in text.lower()

    changed_lines = added_total + removed_total
    score = 1.0
    if expected and not touched_expected_only:
        extra = len(set(touched) - expected)
        score -= min(0.5, extra * 0.15)
    if changed_lines > FREE_LINES:
        score -= min(0.4, (changed_lines - FREE_LINES) * 0.02)
    if noise_acted_on:
        score -= 0.3
    surgical_score = round(max(0.0, min(1.0, score)), 3)

    verdict = {
        "grader": "diff",
        "files_touched": len(touched), "lines_added": added_total, "lines_removed": removed_total,
        "touched_expected_only": touched_expected_only,
        "noise_comment_acted_on": noise_acted_on,
        "surgical_score": surgical_score,
    }
    Path(args.out).write_text(json.dumps(verdict, indent=2))
    print(json.dumps(verdict, indent=2))


if __name__ == "__main__":
    main()
