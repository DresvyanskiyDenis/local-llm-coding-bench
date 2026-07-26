# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""verify_phase4.py — evidence generator for the 11 round-2 task dirs (commit 020e776).

Runs, with the graders UNMODIFIED and no local model / no port touched:

  1. B6 control      -- grade a clean and a hallucinated response through review_grader.py
                        and assert recall is JSON null (not 0.0), plus the digest.py mean
                        consequence of each.
  2. B3/B4/B5        -- execute each grade/verify_bugs.py; declared vs demonstrated.
                        Also re-grade a competent-model answer through review_grader.py,
                        and check every key.json line range brackets a real source line.
  3. C3/C4/C5        -- diff_grader.py + pytest_grader.py round-trips over constructed
                        pass / fail (/ empty, for C4) runs. Reports changed-line counts
                        against diff_grader.FREE_LINES.
  4. D corpus        -- every sha256 in longctx_manifest.json, and byte-identity of the
                        shared core across D3/D4/D5.

Writes eval/results/PHASE4_VERIFICATION.json + .md and prints a compact table.
Exit code 0 iff every check passed.

Network: the manifest's 49 padding sources are `kind: fetched` (pinned raw.githubusercontent
URLs) and have NO on-disk copy in this repo, so they can only be verified by re-fetching.
Cached under $TMPDIR/phase4_pad_src. Run with --offline to skip them (they are then
reported as "unverifiable offline" rather than silently passing).
"""

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HARNESS = Path(__file__).resolve().parent.parent
ROOT = HARNESS.parent.parent
TASKS = ROOT / "eval" / "tasks"
GRADERS = HARNESS / "graders"
RESULTS = ROOT / "eval" / "results"

results = []


def record(area, task, check, ok, number, note=""):
    results.append({"area": area, "task": task, "check": check,
                    "ok": bool(ok), "number": str(number), "note": note})
    print(f"  [{'PASS' if ok else 'FAIL'}] {task:<22} {check:<44} {number}")


def run(cmd, cwd=None):
    return subprocess.run([str(c) for c in cmd], cwd=cwd, capture_output=True, text=True)


def uv(script, *args, cwd=None):
    return run(["uv", "run", "--no-project", str(script), *args], cwd=cwd)


def write_run(d, answer=None, repo_src=None):
    d.mkdir(parents=True, exist_ok=True)
    if answer is not None:
        (d / "answer.txt").write_text(answer)
    if repo_src is not None:
        shutil.copytree(repo_src, d / "repo")
    return d


def sha(b):
    return hashlib.sha256(b).hexdigest()


# --------------------------------------------------------------------------- 1. B6
def check_b6(ws):
    print("\n== 1. B6 control (highest stakes) ==")
    task = TASKS / "B_review" / "B6_control_nobugs"
    key = json.loads((task / "grade" / "key.json").read_text())
    record("B", "B6_control_nobugs", "key.json plants zero bugs",
           len(key.get("bugs", [])) == 0, f"{len(key.get('bugs', []))} bugs")

    cases = {
        "clean": "```json\n[]\n```",
        "hallucinated": ('```json\n[{"file":"src/rate_window.py","line":26,'
                         '"description":"mutable default argument shared across calls"}]\n```'),
    }
    verdicts = {}
    for name, ans in cases.items():
        d = write_run(ws / f"b6_{name}", answer=ans)
        out = d / "grade_review.json"
        p = uv(GRADERS / "review_grader.py", "--task", task, "--run", d, "--out", out)
        if p.returncode != 0:
            record("B", "B6_control_nobugs", f"grader ran ({name})", False, "crash", p.stderr[-300:])
            continue
        raw = out.read_text()
        v = json.loads(raw)
        verdicts[name] = v
        literal_null = re.search(r'"recall":\s*null', raw) is not None
        record("B", "B6_control_nobugs", f"recall is literal JSON null ({name})",
               literal_null and v["recall"] is None,
               f'recall={raw_recall(raw)}')
        record("B", "B6_control_nobugs", f"precision inverts correctly ({name})",
               v["precision"] == (1.0 if name == "clean" else 0.0),
               f'precision={v["precision"]}, fpr={v.get("false_positive_rate")}')

    # digest.py consequence
    import statistics as st

    def mean(xs):
        xs = [x for x in xs if isinstance(x, (int, float))]
        return round(st.mean(xs), 3) if xs else None

    with_null = mean([1.0, 0.667, None])
    with_zero = mean([1.0, 0.667, 0.0])
    record("B", "B6_control_nobugs", "digest.py mean drops null (would drag if 0.0)",
           with_null == 0.834 and with_zero == 0.556,
           f"null->{with_null} vs 0.0->{with_zero}")
    return verdicts


def raw_recall(raw):
    m = re.search(r'"recall":\s*([^,\n]+)', raw)
    return m.group(1).strip() if m else "?"


# ------------------------------------------------------------------- 2. B3/B4/B5
B_ANSWERS = {
    "B3_concurrency_ledger": [
        ("src/ledger.py", 37, "race condition: read-modify-write outside the lock causes a lost update"),
        ("src/ledger.py", 60, "off-by-one: count - 1 returns one entry too many"),
        ("src/ledger.py", 76, "file handle leak: close() never closes the audit file handles"),
    ],
    "B4_io_encoding": [
        ("src/importer.py", 21, "wrong encoding: file opened as latin-1 but the spec says utf-8, mojibake"),
        ("src/importer.py", 40, "swallowed exception: the except branch continues without appending to errors"),
        ("src/importer.py", 53, "off-by-one in batching: batch_size - 1 drops one record per batch"),
    ],
    "B5_temporal_money": [
        ("src/billing.py", 20, "float equality comparison on money is unreliable"),
        ("src/billing.py", 35, "DST bug: converting to UTC shifts the local wall-clock time"),
        ("src/billing.py", 39, "mutable default argument: the dict is shared across calls"),
    ],
}


def check_b345(ws):
    print("\n== 2. B3/B4/B5 planted bugs ==")
    for tid, findings in B_ANSWERS.items():
        task = TASKS / "B_review" / tid
        key = json.loads((task / "grade" / "key.json").read_text())
        declared = len(key["bugs"])

        p = uv(task / "grade" / "verify_bugs.py", cwd=task)
        out = p.stdout
        demonstrated = out.count("demonstrated")
        record("B", tid, "verify_bugs.py: declared vs demonstrated",
               p.returncode == 0 and demonstrated == declared and "ALL BUGS DEMONSTRATED" in out,
               f"{demonstrated}/{declared} demonstrated",
               "" if p.returncode == 0 else p.stderr[-300:])

        # key.json line ranges must bracket real lines of the buggy file
        ok_ranges = 0
        for b in key["bugs"]:
            loc = b["location"]
            src = task / "repo" / loc["file"]
            n = len(src.read_text().splitlines())
            if 1 <= loc["line_start"] <= loc["line_end"] <= n:
                ok_ranges += 1
        record("B", tid, "key.json line ranges inside the file",
               ok_ranges == declared, f"{ok_ranges}/{declared} in range")

        # grader round-trip with a competent answer
        ans = "```json\n" + json.dumps(
            [{"file": f, "line": ln, "description": d} for f, ln, d in findings], indent=1) + "\n```"
        d = write_run(ws / f"b_{tid}", answer=ans)
        o = d / "grade_review.json"
        pr = uv(GRADERS / "review_grader.py", "--task", task, "--run", d, "--out", o)
        v = json.loads(o.read_text()) if pr.returncode == 0 else {}
        record("B", tid, "review_grader round-trip (competent answer)",
               v.get("recall") == 1.0 and v.get("hallucinated") == 0,
               f'recall={v.get("recall")}, precision={v.get("precision")}, halluc={v.get("hallucinated")}')


# ------------------------------------------------------------------- 3. C3/C4/C5
C_EDITS = {
    "C3_scope_creep": {
        "file": "src/shipping.py",
        "valid": [
            ("from __future__ import annotations\n", "from __future__ import annotations\n\nimport math\n"),
            ("    cost = base_rate + package.weight_kg * per_kg_rate\n    return cost",
             "    cost = base_rate + package.weight_kg * per_kg_rate\n    if package.fragile:\n        cost += 3.0\n    return cost"),
            ("if num_packages > 5:", "if num_packages >= 5:"),
            ("days = distance_km // 500", "days = math.ceil(distance_km / 500)"),
        ],
        "trap": [
            ("import math\n", "import math\nfrom dataclasses import dataclass\n"),
            ('class Package:\n    """A package to be shipped."""\n\n    def __init__(self, weight_kg: float, fragile: bool = False):\n        self.weight_kg = weight_kg\n        self.fragile = fragile',
             '@dataclass\nclass Package:\n    """A package to be shipped."""\n\n    weight_kg: float\n    fragile: bool = False'),
        ],
        "pass_answer": "Applied comments 1-3. Skipped comment 4: the dataclass refactor is out of scope.",
        "fail_answer": "Applied all four comments including the dataclass refactor.",
    },
    "C4_already_done": {
        "file": "src/payroll.py",
        "valid": [
            ("    return hours_worked * hourly_rate * 1.5",
             "    regular = 40 * hourly_rate\n    overtime = (hours_worked - 40) * hourly_rate * 1.5\n    return regular + overtime"),
            ("    return int(amount * 100) / 100", "    return round(amount, 2)"),
        ],
        "trap": [
            ("    if hours_worked < 0:\n        return 0.0\n    if hours_worked > max_hours:\n        return max_hours\n    return hours_worked",
             "    return max(0.0, min(hours_worked, max_hours))"),
        ],
        "pass_answer": "Applied comments 1-2. Skipped comment 3: clamp_hours already has the negative guard.",
        "fail_answer": "Applied all three comments; rewrote clamp_hours to add the negative guard.",
        "empty_answer": "The requested guard is already present in clamp_hours; nothing to change.",
    },
    "C5_contradiction": {
        "file": "src/access.py",
        "valid": [
            ("return ROLE_RANK.get(user_role, 0) > ROLE_RANK.get(required_role, 0)",
             "return ROLE_RANK.get(user_role, 0) >= ROLE_RANK.get(required_role, 0)"),
            ("return failed_attempts > max_attempts", "return failed_attempts >= max_attempts"),
            ("return username.lower()", "return username.strip().lower()"),
        ],
        "trap": [
            ("    cents = amount * 100\n    rounded_cents = math.floor(cents + 0.5 + 1e-9)\n    return rounded_cents / 100",
             "    return round(amount, 2)"),
        ],
        "pass_answer": ("Applied comments 1-3. Comments 4 and 5 contradict each other: #4 asks for round() "
                        "(half-to-even) while #5 requires halves always round up per FIN-114. I left "
                        "round_price_to_cents untouched and am flagging the conflict."),
        "pass_answer_silent": ("Applied comments 1-3. Comment 4 looked unnecessary since the code already does "
                              "FIN-114 half-up rounding, so I left it alone."),
        "fail_answer": "Applied all comments; replaced the hand-rolled rounding with round(amount, 2) per comment 4.",
    },
}

FREE_LINES = 15


def apply_edits(repo, rel, subs):
    p = repo / rel
    s = p.read_text()
    for a, b in subs:
        assert a in s, f"anchor missing in {rel}: {a[:50]!r}"
        s = s.replace(a, b, 1)
    p.write_text(s)


def grade_c(task, d):
    dj, pj = d / "grade_diff.json", d / "grade_pytest.json"
    uv(GRADERS / "diff_grader.py", "--task", task, "--run", d, "--out", dj)
    uv(GRADERS / "pytest_grader.py", "--task", task, "--run", d, "--out", pj)
    return json.loads(dj.read_text()), (json.loads(pj.read_text()) if pj.exists() else {})


def check_c(ws):
    print("\n== 3. C3/C4/C5 diff_grader round-trips ==")
    for tid, spec in C_EDITS.items():
        task = TASKS / "C_edit" / tid
        rel = spec["file"]

        # pass case
        d = write_run(ws / f"c_{tid}_pass", answer=spec["pass_answer"], repo_src=task / "repo")
        apply_edits(d / "repo", rel, spec["valid"])
        dv, pv = grade_c(task, d)
        changed = dv["lines_added"] + dv["lines_removed"]
        clean = dv["noise_comment_acted_on"] is False and changed <= FREE_LINES and dv["surgical_score"] == 1.0
        record("C", tid, f"PASS case clean, changed lines vs FREE_LINES={FREE_LINES}",
               clean, f"{changed} lines (limit {FREE_LINES}), surgical={dv['surgical_score']}, pytest={pv.get('pass_rate')}",
               "COIN-FLIP RISK: within 1 of the limit" if changed >= FREE_LINES - 1 else "")

        # fail case
        d = write_run(ws / f"c_{tid}_fail", answer=spec["fail_answer"], repo_src=task / "repo")
        apply_edits(d / "repo", rel, spec["valid"] + spec["trap"])
        dv, pv = grade_c(task, d)
        record("C", tid, "FAIL case: trap fires",
               dv["noise_comment_acted_on"] is True and dv["surgical_score"] < 1.0,
               f"acted_on={dv['noise_comment_acted_on']}, surgical={dv['surgical_score']}, pytest={pv.get('pass_rate')}")

        # C4 empty diff
        if tid == "C4_already_done":
            d = write_run(ws / "c_C4_empty", answer=spec["empty_answer"], repo_src=task / "repo")
            dv, pv = grade_c(task, d)
            changed = dv["lines_added"] + dv["lines_removed"]
            record("C", tid, "EMPTY diff reads as restraint on diff side",
                   dv["noise_comment_acted_on"] is False and dv["surgical_score"] == 1.0,
                   f"changed={changed}, surgical={dv['surgical_score']} (NOT a failure to respond)")
            record("C", tid, "EMPTY diff separated from correct answer by pytest half",
                   pv.get("pass_rate", 1.0) < 1.0,
                   f"pytest={pv.get('pass_rate')} ({pv.get('passed')}/{pv.get('total')}) vs 1.0 for the correct edit",
                   "diff_grader ALONE cannot tell them apart (both surgical=1.0)")

        # C5 silent-but-correct case
        if tid == "C5_contradiction":
            d = write_run(ws / "c_C5_pass_silent", answer=spec["pass_answer_silent"], repo_src=task / "repo")
            apply_edits(d / "repo", rel, spec["valid"])
            dv, _ = grade_c(task, d)
            ent = {e["kind"]: e for e in dv.get("noise", [])}
            surf_named = None
            dn = ws / f"c_{tid}_pass" / "grade_diff.json"
            if dn.exists():
                ent_named = {e["kind"]: e for e in json.loads(dn.read_text()).get("noise", [])}
                surf_named = ent_named.get("contradiction", {}).get("conflict_surfaced")
            record("C", tid, "contradiction signal: named vs silent (documented false-negative)",
                   surf_named is True and ent.get("contradiction", {}).get("conflict_surfaced") is False,
                   f"named={surf_named}, silent={ent.get('contradiction', {}).get('conflict_surfaced')} "
                   f"(both code-correct: acted_on={ent.get('must_survive', {}).get('acted_on')})",
                   "keyword match only -- cannot tell 'right for the right reason, unstated' from 'never noticed'")


# ------------------------------------------------------------------------ 4. D
def check_d(offline):
    print("\n== 4. D corpus integrity ==")
    dt = TASKS / "D_text"
    man = json.loads((dt / "longctx_manifest.json").read_text())

    total_refs = 1 + len(man["core"]["sources"]) + len(man["padding"]["order"])

    # assembled core
    core_bytes = (dt / "longctx_core" / "core.md").read_bytes()
    record("D", "longctx_core", "assembled core.md sha256 matches manifest",
           sha(core_bytes) == man["core"]["sha256"], f"{sha(core_bytes)[:16]}...")

    # on-disk core sources
    ok = 0
    parts = []
    for s in man["core"]["sources"]:
        p = ROOT / s["path"]
        if not p.exists():
            continue
        data = p.read_bytes()
        br = s.get("byte_range_used")
        used = data[br[0]:br[1]] if br else data
        parts.append(used)
        if sha(used) == s["sha256"]:
            ok += 1
    n_core = len(man["core"]["sources"])
    record("D", "manifest.core", "on-disk core source sha256s",
           ok == n_core, f"{ok}/{n_core} OK")
    record("D", "manifest.core", "core.md == sources joined by blank line",
           b"\n".join(parts) == core_bytes, f"{len(b'\n'.join(parts))} == {len(core_bytes)} bytes")

    # padding: fetched, no on-disk copy
    pad = man["padding"]["order"]
    cache = Path(os.environ.get("TMPDIR", tempfile.gettempdir())) / "phase4_pad_src"
    cache.mkdir(parents=True, exist_ok=True)
    if offline:
        record("D", "manifest.padding", "fetched padding sha256s (kind=fetched, NOT on disk)",
               False, f"0/{len(pad)} — skipped (--offline)",
               "these 49 refs have no on-disk file; only re-fetch can verify them")
        pad_ok = 0
    else:
        pad_ok = 0
        for i, s in enumerate(pad):
            f = cache / f"{i:02d}.bin"
            if not f.exists() or f.stat().st_size == 0:
                run(["curl", "-sSfL", "-o", str(f), s["url"]])
            if not f.exists() or f.stat().st_size == 0:
                continue
            data = f.read_bytes()
            br = s.get("byte_range_used")
            used = data[br[0]:br[1]] if br else data
            if sha(used) == s["sha256"]:
                pad_ok += 1
        record("D", "manifest.padding", "fetched padding sha256s (re-fetched from pinned commits)",
               pad_ok == len(pad), f"{pad_ok}/{len(pad)} OK")

    record("D", "longctx_manifest", "total sha256 refs verified",
           (1 + ok + pad_ok) == total_refs, f"{1 + ok + pad_ok}/{total_refs}")

    # shared core across D3/D4/D5
    import difflib
    corelines = core_bytes.decode("utf8", "replace").splitlines()
    tasks3 = ["D3_longctx_30k", "D4_longctx_60k", "D5_longctx_100k"]
    extracted, frags = {}, {}
    for t in tasks3:
        lines = (dt / t / "source" / "corpus.md").read_text(errors="replace").splitlines()
        sm = difflib.SequenceMatcher(None, corelines, lines, autojunk=False)
        blocks = [b for b in sm.get_matching_blocks() if b.size > 0]
        got = []
        for b in blocks:
            got.extend(corelines[b.a:b.a + b.size])
        extracted[t] = sha("\n".join(got).encode())
        frags[t] = (sum(b.size for b in blocks), len(blocks))
    complete = all(frags[t][0] == len(corelines) for t in tasks3)
    identical = len(set(extracted.values())) == 1
    record("D", "D3/D4/D5", "core present in full in all three corpora",
           complete, ", ".join(f"{t.split('_')[0]}={frags[t][0]}/{len(corelines)}" for t in tasks3))
    record("D", "D3/D4/D5", "extracted core byte-identical across the ladder",
           identical, f"{list(extracted.values())[0][:16]}... x3, "
                      f"fragments={[frags[t][1] for t in tasks3]}")

    # shared prompt/rubric/key_points
    same = []
    for name in ("PROMPT.md", "grade/key_points.json", "grade/rubric.md"):
        hs = {sha((dt / t / name).read_bytes()) for t in tasks3}
        hs |= {sha((dt / "longctx_shared" / name).read_bytes())}
        same.append(len(hs) == 1)
    record("D", "D3/D4/D5", "PROMPT/rubric/key_points identical + match longctx_shared",
           all(same), f"{sum(same)}/3 identical")

    # reps asymmetry (the ladder's controlled variable)
    reps = {t: json.loads((dt / t / "meta.json").read_text()).get("reps", "<absent -> stage default>")
            for t in tasks3}
    record("D", "D3/D4/D5", "rep count held constant across the ladder",
           len({str(v) for v in reps.values()}) == 1,
           "; ".join(f"{t.split('_')[0]}={v}" for t, v in reps.items()),
           "D3 falls through to orchestrate.py default_reps=[1,2,3]; D4/D5 pinned to 1")


# ---------------------------------------------------------------------- report
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true")
    args = ap.parse_args()

    ws = Path(tempfile.mkdtemp(prefix="phase4_", dir=os.environ.get("TMPDIR")))
    print(f"workspace: {ws}")
    check_b6(ws)
    check_b345(ws)
    check_c(ws)
    check_d(args.offline)

    npass = sum(1 for r in results if r["ok"])
    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / "PHASE4_VERIFICATION.json").write_text(json.dumps(
        {"checks": results, "passed": npass, "total": len(results)}, indent=2))

    lines = ["# Phase 4 task verification", "",
             f"`{npass}/{len(results)}` checks passed. Regenerate: "
             "`uv run eval/harness/ops/verify_phase4.py`.", "",
             "| Area | Task | Check | Verdict | Number |", "|---|---|---|---|---|"]
    for r in results:
        note = f"<br>_{r['note']}_" if r["note"] else ""
        lines.append(f"| {r['area']} | `{r['task']}` | {r['check']}{note} | "
                     f"{'PASS' if r['ok'] else 'FAIL'} | {r['number']} |")
    (RESULTS / "PHASE4_VERIFICATION.md").write_text("\n".join(lines) + "\n")

    print(f"\n{npass}/{len(results)} checks passed")
    print(f"wrote {RESULTS / 'PHASE4_VERIFICATION.md'}")
    return 0 if npass == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
