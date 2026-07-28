# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""review_grader.py — semi-objective planted-bug recall/precision verdict for B_review,
per CONTRACT.md §2.

Mandated answer.txt format (verified against all six landed B PROMPT.md, B1-B6 --
identical wording in all, 2026-07-28): a single fenced ```json code block containing a
JSON array of objects with exactly the keys file/line/description -- no bullet fallback,
no alternate key names (location/line_end). Findings are always single-line.

Matching against grade/key.json (schema confirmed live: {"bugs": [{id, location:
{file, line_start, line_end}, function, description, synonyms:[...], severity}, ...]}):
a finding confidently matches a planted bug when its location overlaps (same file, line
within [line_start, line_end], no fuzz -- the ranges already carry their own slack) AND
its description matches one of the bug's synonyms, its id, or its own canonical
description; a finding matching on only one signal is "ambiguous" (saved for Opus
adjudication, never guessed); everything else counts toward hallucinated/missed.

Control tasks (round 2, e.g. B6): grade/key.json plants nothing. Recognised as a control
via EITHER an explicit `"control": true` flag OR a bare empty `"bugs": []` list -- both
forms are honoured. `planted` is then 0, so `recall` is reported as `null` (never `0.0`;
recall is undefined when nothing was planted, not zero). `precision` collapses to the
control-specific rule ANY finding on a no-bug file is a false positive, so
`precision = 1.0` if the model reported nothing, else `0.0` -- and the verdict gains a
`false_positive_rate` field (findings / 1) that is present ONLY for control tasks, so
non-control verdicts keep exactly today's key set.

Usage:
    uv run review_grader.py --task tasks/B_review/B1_customer_cleaning \\
        --run runs/qwen__q5__B_review__B1__rep1 --out runs/.../grade_review.json
"""

import argparse
import json
import re
from pathlib import Path

JSON_BLOCK_RE = re.compile(r"```(?:json)?\s*(\[.*?\])\s*```", re.S)


def parse_findings(answer_text):
    m = JSON_BLOCK_RE.search(answer_text)
    if not m:
        return []
    try:
        data = json.loads(m.group(1))
    except json.JSONDecodeError:
        return []
    if not isinstance(data, list):
        return []
    findings = []
    for item in data:
        if not isinstance(item, dict) or not all(k in item for k in ("file", "line", "description")):
            continue
        findings.append({
            "file": item["file"], "line_start": item["line"], "line_end": item["line"],
            "description": str(item["description"]),
        })
    return findings


def normalize_location(loc):
    if not isinstance(loc, dict):
        return None, None, None
    return loc.get("file"), loc.get("line_start"), loc.get("line_end", loc.get("line_start"))


def paths_match(a, b):
    if not a or not b:
        return False
    pa = [c for c in Path(a).parts if c not in (".", "repo")]
    pb = [c for c in Path(b).parts if c not in (".", "repo")]
    return pa == pb


def lines_overlap(f_start, f_end, k_start, k_end):
    if None in (f_start, f_end, k_start, k_end):
        return False
    return f_start <= k_end and k_start <= f_end


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--task", required=True)
    ap.add_argument("--run", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    task_dir = Path(args.task)
    run_dir = Path(args.run)

    answer_text = (run_dir / "answer.txt").read_text() if (run_dir / "answer.txt").exists() else ""
    key_doc = json.loads((task_dir / "grade" / "key.json").read_text())
    key = key_doc.get("bugs", [])
    is_control = bool(key_doc.get("control")) or not key
    findings = parse_findings(answer_text)

    matched_ids, missed_ids, ambiguous = [], [], []
    consumed = set()

    for bug in key:
        bfile, bstart, bend = normalize_location(bug.get("location"))
        signals = ([s.lower() for s in bug.get("synonyms", [])]
                   + [str(bug.get("id", "")).lower(), (bug.get("description") or "").lower()])
        confident_idx = ambiguous_idx = None
        for i, f in enumerate(findings):
            if i in consumed:
                continue
            loc_ok = paths_match(f["file"], bfile) and lines_overlap(f["line_start"], f["line_end"], bstart, bend)
            desc = f["description"].lower()
            syn_ok = any(s and (s in desc or desc in s) for s in signals)
            if loc_ok and syn_ok:
                confident_idx = i
                break
            if (loc_ok or syn_ok) and ambiguous_idx is None:
                ambiguous_idx = i
        if confident_idx is not None:
            matched_ids.append(bug["id"])
            consumed.add(confident_idx)
        elif ambiguous_idx is not None:
            ambiguous.append({"finding": findings[ambiguous_idx]["description"], "closest_id": bug["id"]})
            consumed.add(ambiguous_idx)
        else:
            missed_ids.append(bug["id"])

    planted = len(key)
    found = len(matched_ids)
    hallucinated = max(len(findings) - len(consumed), 0)

    verdict = {
        "grader": "review",
        "planted": planted, "found": found, "hallucinated": hallucinated,
        "recall": round(found / planted, 3) if planted else None,
        "precision": round(found / (found + hallucinated), 3) if (found + hallucinated) else None,
        "matched_ids": matched_ids, "missed_ids": missed_ids,
        "ambiguous": ambiguous,
    }
    if is_control:
        # No bugs were planted: recall stays null (already true above, planted == 0).
        # Precision is redefined -- any reported finding on a no-bug file is a false
        # positive, so a clean (empty) report is perfect precision, and any finding at
        # all is zero precision, regardless of the found/hallucinated denominator.
        verdict["precision"] = 1.0 if not findings else 0.0
        verdict["false_positive_rate"] = len(findings) / 1
    Path(args.out).write_text(json.dumps(verdict, indent=2))
    print(json.dumps(verdict, indent=2))


if __name__ == "__main__":
    main()
