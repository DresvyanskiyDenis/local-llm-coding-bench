# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""test_grader_regression.py — round-2 grader regression gate (review_grader.py,
diff_grader.py), per IMPLEMENTATION_PLAN.md §7 / §9 phase-3 gate.

Re-grades every checked-in fixture under `_fixtures/{review,diff}/` with the CURRENT
graders and asserts the verdict equals the checked-in expected JSON under
`_fixtures/expected/{review,diff}/`, exactly (deep-equal, key-for-key).

Two fixture classes:
  - Backward-compat fixtures (task_B1, task_B2, task_C1, task_C2 -- real round-1 task
    definitions, unmodified key.json/noise.json, no "control"/"kind" opt-in fields).
    Their expected/*.json was captured from the PRE-change graders (git HEAD) on the
    exact same fixture inputs -- see the grader-change report for the byte-diff proof.
    A failure here means a round-2 grader change broke round-1 comparability.
  - New-path fixtures (task_B6_*, task_C5_contradiction, task_C_multi) exercise the
    round-2 additions: the zero-planted-bug control path, and noise.json's `kind`/
    multi-entry schema (including "contradiction"'s answer.txt keyword-match path).

IMPORTANT LIMITATION (recorded, not hidden): the literal round-1 answer.txt / edited
repo/ trees are NOT recoverable from this repo's committed artifacts -- `eval/runs/` is
gone and the round-1 result JSONs (`eval/results/*.json`) store only the aggregated
grade verdict + a path reference to `eval/runs/.../answer.txt`, never the raw text or
tree. The backward-compat fixtures here are therefore reconstructed answer.txt /
edited-repo inputs (using the REAL grade/key.json and grade/noise.json from
B1/B2/C1/C2, and, for C1/C2, the real grade/ref_solution.py as the "clean" edit) built
to exercise the same matching/diffing code paths and a spread of recall/precision/
surgical_score values -- not a byte-for-byte replay of a specific round-1 unit's raw
output. This is disclosed rather than silently assumed away.

Usage:
    uv run eval/harness/graders/test_grader_regression.py
Exits 0 and prints PASS per case if every fixture matches; exits 1 and prints the diff
for the first mismatch otherwise.
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
FIXTURES = HERE / "_fixtures"
EXPECTED = FIXTURES / "expected"

REVIEW_CASES = [
    # (task_dir, run_dir, expected_json)
    ("review/task_B1", "review/run_B1_recall_667", "review/run_B1_recall_667.json"),
    ("review/task_B1", "review/run_B1_recall_0", "review/run_B1_recall_0.json"),
    ("review/task_B2", "review/run_B2_recall_1", "review/run_B2_recall_1.json"),
    ("review/task_B2", "review/run_B2_ambiguous", "review/run_B2_ambiguous.json"),
    ("review/task_B6_control_flag", "review/run_B6_clean", "review/B6_flag_clean.json"),
    ("review/task_B6_control_flag", "review/run_B6_false_positive", "review/B6_flag_fp.json"),
    ("review/task_B6_bare_empty", "review/run_B6_clean", "review/B6_bare_clean.json"),
    ("review/task_B6_bare_empty", "review/run_B6_false_positive", "review/B6_bare_fp.json"),
]

DIFF_CASES = [
    ("diff/task_C1", "diff/run_C1_clean", "diff/run_C1_clean.json"),
    ("diff/task_C1", "diff/run_C1_noise_acted", "diff/run_C1_noise_acted.json"),
    ("diff/task_C2", "diff/run_C2_clean", "diff/run_C2_clean.json"),
    ("diff/task_C2", "diff/run_C2_noise_acted", "diff/run_C2_noise_acted.json"),
    ("diff/task_C5_contradiction", "diff/run_C5_surfaced", "diff/C5_surfaced.json"),
    ("diff/task_C5_contradiction", "diff/run_C5_not_surfaced", "diff/C5_not_surfaced.json"),
    ("diff/task_C5_contradiction", "diff/run_C5_no_answer", "diff/C5_no_answer.json"),
    ("diff/task_C_multi", "diff/run_C_multi_none_acted", "diff/C_multi_none.json"),
    ("diff/task_C_multi", "diff/run_C_multi_one_acted", "diff/C_multi_one.json"),
    ("diff/task_C_multi", "diff/run_C_multi_both_acted", "diff/C_multi_both.json"),
]

# Backward-compat subset: these MUST come from real, untagged/non-control round-1 task
# definitions. Kept as an explicit allowlist so a future edit to this file can't
# accidentally weaken the gate by mislabeling a new-path case as backward-compat.
BACKWARD_COMPAT_RUN_DIRS = {
    "review/run_B1_recall_667", "review/run_B1_recall_0",
    "review/run_B2_recall_1", "review/run_B2_ambiguous",
    "diff/run_C1_clean", "diff/run_C1_noise_acted",
    "diff/run_C2_clean", "diff/run_C2_noise_acted",
}


def run_grader(script, task_dir, run_dir, out_path):
    cmd = ["uv", "run", str(HERE / script),
           "--task", str(FIXTURES / task_dir),
           "--run", str(FIXTURES / run_dir),
           "--out", str(out_path)]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"{script} malfunctioned on {task_dir}/{run_dir}:\n{proc.stderr}")
    return json.loads(out_path.read_text())


def main():
    failures = []
    backward_compat_checked = 0

    with tempfile.TemporaryDirectory(prefix="grader_regression_") as tmp:
        tmp = Path(tmp)

        for task_dir, run_dir, expected_rel in REVIEW_CASES:
            out_path = tmp / f"{run_dir.replace('/', '_')}.json"
            actual = run_grader("review_grader.py", task_dir, run_dir, out_path)
            expected = json.loads((EXPECTED / expected_rel).read_text())
            tag = "[backward-compat]" if run_dir in BACKWARD_COMPAT_RUN_DIRS else "[new-path]"
            if run_dir in BACKWARD_COMPAT_RUN_DIRS:
                backward_compat_checked += 1
            if actual == expected:
                print(f"PASS {tag} review {task_dir} / {run_dir}")
            else:
                failures.append((f"review {task_dir} / {run_dir}", expected, actual))

        for task_dir, run_dir, expected_rel in DIFF_CASES:
            out_path = tmp / f"{run_dir.replace('/', '_')}.json"
            actual = run_grader("diff_grader.py", task_dir, run_dir, out_path)
            expected = json.loads((EXPECTED / expected_rel).read_text())
            tag = "[backward-compat]" if run_dir in BACKWARD_COMPAT_RUN_DIRS else "[new-path]"
            if run_dir in BACKWARD_COMPAT_RUN_DIRS:
                backward_compat_checked += 1
            if actual == expected:
                print(f"PASS {tag} diff {task_dir} / {run_dir}")
            else:
                failures.append((f"diff {task_dir} / {run_dir}", expected, actual))

    print(f"\n{backward_compat_checked}/{len(BACKWARD_COMPAT_RUN_DIRS)} backward-compat "
          f"fixtures re-graded byte-identically to the pre-change graders.")

    if failures:
        print(f"\n{len(failures)} FAILURE(S):", file=sys.stderr)
        for name, expected, actual in failures:
            print(f"\n--- {name} ---", file=sys.stderr)
            print("expected:", json.dumps(expected, indent=2), file=sys.stderr)
            print("actual:  ", json.dumps(actual, indent=2), file=sys.stderr)
        sys.exit(1)

    print(f"\nALL {len(REVIEW_CASES) + len(DIFF_CASES)} FIXTURES PASSED.")


if __name__ == "__main__":
    main()
