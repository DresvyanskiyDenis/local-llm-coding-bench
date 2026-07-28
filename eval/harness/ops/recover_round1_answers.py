#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# ///
"""Recover round-1 D_text answer text from OpenCode's own session store.

`<rundir>/answer.txt` (eval/runs/, gitignored + regenerable) is the ONLY place the round-1
driver wrote the verbatim model answer, and it is gone (0 entries on this machine, never
tracked). But eval/results/<unit_id>.json's `driver.session_id` is a live OpenCode session id,
and OpenCode keeps its OWN session store (~/.local/share/opencode/opencode.db) independently
of this repo's eval/runs/ tree — it was never gitignored or deleted. `opencode export <sid>`
(CONTRACT.md §3 step 3 — the exact mechanism the driver used originally) still resolves.

This script walks the round-1 D_text rep1 unit JSONs, exports each session, extracts the
FINAL assistant message's text part (verified across all 30 round-1 sessions: exactly one
`text` part in the last assistant message, uniformly), and writes it to a NEW tracked
location — it does not touch eval/runs/ (gitignored) and does not modify any existing
eval/results/*.json (round-1 results are immutable).

Usage:
    uv run eval/harness/ops/recover_round1_answers.py --suite D_text --round 1
    uv run eval/harness/ops/recover_round1_answers.py --suite D_text --round 1 --dry-run
"""

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

OPS_DIR = Path(__file__).resolve().parent
HARNESS_DIR = OPS_DIR.parent
EVAL_DIR = HARNESS_DIR.parent
RESULTS_DIR = EVAL_DIR / "results"
CONFIGS_PATH = HARNESS_DIR / "configs.json"


# A DELIBERATE copy of pairwise_judge.py's load_configs, not an oversight: importing it needs
# sys.path surgery AND drags `numpy>=1.26` into a recovery script whose PEP 723 header declares
# no dependencies at all — deduplicating it makes the data-loss recovery path the fragile one.
def load_configs():
    raw = json.loads(CONFIGS_PATH.read_text())
    out, seen = [], set()
    for c in raw:
        if c.get("broken"):
            continue
        cid = f"{c['model']}__{c['quant']}"
        if cid in seen:
            continue
        seen.add(cid)
        out.append({"id": cid, "model": c["model"], "quant": c["quant"]})
    return out


def discover_tasks(suite, round_):
    if suite == "D_text" and round_ == 1:
        return ["D1_summarize_mtp", "D2_dedup_approaches"]
    tasks = set()
    for p in RESULTS_DIR.glob(f"*__{suite}__*__rep{round_}.json"):
        data = json.loads(p.read_text())
        t = data.get("task")
        if t:
            tasks.add(t)
    return sorted(tasks)


def export_session(session_id):
    """Returns (parsed_json_or_None, error_str_or_None)."""
    try:
        proc = subprocess.run(
            ["opencode", "export", session_id],
            capture_output=True,
            text=True,
            timeout=60,
        )
    except subprocess.TimeoutExpired:
        return None, "opencode export timed out"
    if proc.returncode != 0:
        return None, f"opencode export exited {proc.returncode}: {proc.stderr[:300]}"
    # `opencode export <sid>` prints a "Exporting session: <sid>" line before the JSON body.
    stdout = proc.stdout
    brace = stdout.find("{")
    if brace == -1:
        return None, "no JSON object found in opencode export output"
    try:
        return json.loads(stdout[brace:]), None
    except json.JSONDecodeError as e:
        return None, f"opencode export output did not parse as JSON: {e}"


def extract_final_answer_text(export_obj):
    """Walk messages backwards for the last assistant message with >=1 `text` part.
    Concatenates multiple text parts if present (not observed in round-1 data, but handled
    defensively rather than assumed)."""
    messages = export_obj.get("messages") or []
    for msg in reversed(messages):
        info = msg.get("info") or {}
        if info.get("role") != "assistant":
            continue
        texts = [
            p.get("text", "") for p in msg.get("parts", []) if p.get("type") == "text"
        ]
        if texts:
            return "\n\n".join(t for t in texts if t.strip()).strip(), len(texts)
    return None, 0


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--suite", default="D_text")
    ap.add_argument("--round", type=int, default=1)
    ap.add_argument(
        "--out-dir", default=None, help="default: eval/results/round1_answers/<suite>/"
    )
    ap.add_argument(
        "--force", action="store_true", help="re-export even if the .txt already exists"
    )
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="report what would be recovered, write nothing",
    )
    args = ap.parse_args()

    out_dir = (
        Path(args.out_dir)
        if args.out_dir
        else RESULTS_DIR / "round1_answers" / args.suite
    )

    configs = load_configs()
    tasks = discover_tasks(args.suite, args.round)
    print(
        f"[recover] {len(configs)} configs x {len(tasks)} tasks = {len(configs) * len(tasks)} units, "
        f"suite={args.suite} round={args.round}"
    )

    manifest = {}
    n_recovered = n_already_present = n_missing_unit_json = n_missing_session_id = 0
    n_export_failed = n_no_text_found = 0

    for c in configs:
        for t in tasks:
            unit_id = f"{c['model']}__{c['quant']}__{args.suite}__{t}__rep{args.round}"
            unit_path = RESULTS_DIR / f"{unit_id}.json"
            out_path = out_dir / f"{unit_id}.txt"

            if not unit_path.exists():
                n_missing_unit_json += 1
                manifest[unit_id] = {"status": "missing_unit_json"}
                continue

            unit = json.loads(unit_path.read_text())
            session_id = (unit.get("driver") or {}).get("session_id")
            if not session_id:
                n_missing_session_id += 1
                manifest[unit_id] = {"status": "missing_session_id"}
                continue

            if out_path.exists() and not args.force:
                n_already_present += 1
                manifest[unit_id] = {
                    "status": "already_present",
                    "session_id": session_id,
                    "out_path": str(out_path),
                }
                continue

            export_obj, err = export_session(session_id)
            if export_obj is None:
                n_export_failed += 1
                manifest[unit_id] = {
                    "status": "export_failed",
                    "session_id": session_id,
                    "error": err,
                }
                print(f"[recover]   FAILED {unit_id} (session {session_id}): {err}")
                continue

            text, n_text_parts = extract_final_answer_text(export_obj)
            if not text:
                n_no_text_found += 1
                manifest[unit_id] = {
                    "status": "no_final_text",
                    "session_id": session_id,
                }
                print(
                    f"[recover]   NO TEXT {unit_id} (session {session_id}) — final assistant "
                    f"message has no non-empty text part"
                )
                continue

            manifest[unit_id] = {
                "status": "recovered",
                "session_id": session_id,
                "n_text_parts_in_final_message": n_text_parts,
                "char_len": len(text),
                "word_count": len(text.split()),
                "out_path": str(out_path),
                "recovered_ts": datetime.now(timezone.utc).isoformat(),
                "recovery_method": "opencode export <session_id> -> last assistant message's "
                "text part(s) (CONTRACT.md §3 step 3 mechanism)",
            }
            if not args.dry_run:
                out_dir.mkdir(parents=True, exist_ok=True)
                out_path.write_text(text)
            n_recovered += 1

    print(
        f"[recover] recovered={n_recovered} already_present={n_already_present} "
        f"export_failed={n_export_failed} no_text_found={n_no_text_found} "
        f"missing_unit_json={n_missing_unit_json} missing_session_id={n_missing_session_id}"
    )

    if not args.dry_run:
        out_dir.mkdir(parents=True, exist_ok=True)
        manifest_path = out_dir / "_manifest.json"
        manifest_path.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "ts": datetime.now(timezone.utc).isoformat(),
                    "suite": args.suite,
                    "round": args.round,
                    "n_recovered": n_recovered,
                    "n_already_present": n_already_present,
                    "n_export_failed": n_export_failed,
                    "n_no_text_found": n_no_text_found,
                    "n_missing_unit_json": n_missing_unit_json,
                    "n_missing_session_id": n_missing_session_id,
                    "units": manifest,
                },
                indent=2,
            )
        )
        print(f"[recover] wrote {manifest_path}")
    else:
        print("[recover] --dry-run: wrote nothing")

    return 0 if (n_export_failed == 0 and n_no_text_found == 0) else 1


if __name__ == "__main__":
    sys.exit(main())
