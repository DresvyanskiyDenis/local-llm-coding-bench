#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "httpx>=0.27",
#     "absl-py>=2.0",
#     "langdetect>=1.0.9",
#     "nltk>=3.8",
#     "immutabledict>=4.0",
# ]
# ///
"""IFEval adapter — generate + score, per `harness/configs.json` config.

Lane 2 (external, model-level, not harness-level — see IMPLEMENTATION_PLAN.md §3):
single-turn, no system prompt, no agent/tools, straight to `/v1/chat/completions`.
Scoring reuses the vendored google-research checker unmodified
(`vendor/instruction_following_eval/evaluation_lib.py`) — see `vendor/PROVENANCE.md`.

Usage:
    uv run run_ifeval.py --only opus --limit 20
    uv run run_ifeval.py --only opus                      # full 541-prompt run
    uv run run_ifeval.py --score-only fixtures/synthetic_responses.jsonl \\
        --model synthetic --quant test                     # offline, no inference, no model needed

Serve lifecycle (serve/wait-for-ready/unload) is IMPORTED from harness/orchestrate.py, not
reimplemented (IMPLEMENTATION_PLAN.md §2 ground rules). Requires
`eval/harness/ops/serving_mode.sh eval` to have been run first — this script refuses to launch
against :8888 if llama-swap still owns it (§3.5 bite 1).
"""

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

IFEVAL_DIR = Path(__file__).resolve().parent
EVAL_DIR = IFEVAL_DIR.parent.parent
HARNESS_DIR = EVAL_DIR / "harness"
VENDOR_DIR = IFEVAL_DIR / "vendor"
NLTK_DATA_DIR = IFEVAL_DIR / "nltk_data"
DATA_PATH = IFEVAL_DIR / "data" / "input_data.jsonl"
WORK_DIR = IFEVAL_DIR / "_work"
RESULTS_DIR = EVAL_DIR / "results"
DEFAULT_CONFIGS_PATH = HARNESS_DIR / "configs.json"

# nltk >= 3.10 sandboxes reads/writes to NLTK_DATA / nltk.data.path (see bootstrap_nltk.py);
# this MUST happen before nltk is imported anywhere in this process — including transitively,
# via `instructions_util.py` importing nltk at module load time. Do this before touching
# sys.path or importing the vendored package.
os.environ.setdefault("NLTK_DATA", str(NLTK_DATA_DIR))

sys.path.insert(0, str(HARNESS_DIR))
sys.path.insert(0, str(VENDOR_DIR))

from orchestrate import (  # noqa: E402
    api_key as orchestrate_api_key,
    lsof_listen_pids,
    serve_config,
    unload,
)
from instruction_following_eval import evaluation_lib  # noqa: E402

import random  # noqa: E402

import httpx  # noqa: E402
import langdetect  # noqa: E402

# langdetect is non-deterministic by construction: every detect() call builds a fresh
# Detector with its own random.Random(), reseeded from DetectorFactory.seed — which defaults
# to None, i.e. OS entropy, on EVERY call (confirmed by reading detector.py's _detect_block:
# `self.random.seed(self.seed)` runs per detect(), not once per process). Three vendored
# checkers call langdetect.detect() directly: language:response_language, and, less
# obviously, change_case:english_capital / change_case:english_lowercase (both also assert
# `langdetect.detect(value) == "en"`). Left unseeded, prompt_level_strict/loose are NOT
# reproducible run-to-run for any config with one of those three instruction types — this was
# caught empirically (two consecutive --score-only runs over the identical, byte-unchanged
# synthetic fixture produced different prompt_level_loose). Seeding is upstream's own
# documented fix (langdetect README: "DetectorFactory.seed = 0" for consistent results) and is
# adapter-side configuration of a dependency, not a change to vendored code.
langdetect.DetectorFactory.seed = 0

# A second, independent non-determinism source: keywords:letter_frequency's
# build_description(letter=...) (vendor instructions.py) validates `letter` as a single a-z
# character (`ord(letter.lower())` in [97, 122]); any dataset kwarg outside that range (e.g. a
# real prompt in data/input_data.jsonl asks for hashtag frequency with letter="#", ord 35) is
# silently treated as "no letter given" and replaced via `random.choice(string.ascii_letters)`
# — Python's global `random` module, not langdetect's. This is a genuine upstream dataset/
# checker quirk (confirmed by direct instantiation: the same build_description(letter="#", ...)
# call resolves to a different self._letter on repeated calls), and it affects the real
# 541-prompt set too, not just this adapter's fixture — any live model answering that exact
# prompt is scored against whichever random a-z letter this process happened to draw. Seeding
# the global RNG once, up front, makes a given process's scoring run reproducible; it does not
# and cannot fix the checker's own information loss (the real target letter "#" is gone by the
# time build_description returns) — that is upstream vendored behavior, left untouched.
random.seed(0)

API_BASE_DEFAULT = "http://127.0.0.1:8888/v1"
MAX_TOKENS = 1280
# §3.5 bite 3: an explicit neutral sampling block, sent verbatim on every request — never
# relying on server-side per-model defaults (sampler-coder carries --presence-penalty 1.5,
# sampler-qwen does not; that is a real and uneven distortion for an IF-following measurement).
NEUTRAL_SAMPLING = {
    "temperature": 0,
    "top_p": 1,
    "top_k": 0,
    "min_p": 0,
    "presence_penalty": 0,
    "frequency_penalty": 0,
}
# CONFIRMED LEAK (eval/external/reasoning_leak_probe.json, probed live against qwen4):
# choices[0].message keys are exactly ['content','refusal','role'] — no reasoning_content,
# no reasoning field, completion_tokens_details.reasoning_tokens is 0 — this server does NOT
# separate reasoning; content begins with a literal "<think>". Stripping <think>...</think>
# (and equivalent wrapper tags) out of content is therefore the ONLY path; there is no
# separate field to prefer instead.
REASONING_TAG_RE = re.compile(r"<(think|reasoning|thinking)>.*?</\1>", re.IGNORECASE | re.DOTALL)
# Matches an OPENING tag with no matching close — the truncation case: a thinking model that
# never got past reasoning within max_tokens returns finish_reason "length" and content that
# is pure unterminated reasoning. REASONING_TAG_RE above cannot match it (no closing tag), so
# anything from this point onward must be discarded, never scored as the model's answer.
OPEN_REASONING_TAG_RE = re.compile(r"<(?:think|reasoning|thinking)>", re.IGNORECASE)


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def atomic_write_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2))
    os.replace(tmp, path)


def vendor_sha256():
    """sha256 over the vendored scoring code, concatenated in a fixed order — a single
    number a result file can carry to prove which checker version graded it (PROVENANCE.md
    records the same files per-file; this is the same integrity check, one hash)."""
    files = sorted((VENDOR_DIR / "instruction_following_eval").glob("*.py"))
    h = hashlib.sha256()
    for f in files:
        h.update(f.read_bytes())
    return h.hexdigest()


# ---------------------------------------------------------------------------
# configs.json (read-only; --only filters on "model")
# ---------------------------------------------------------------------------

def load_configs(path):
    configs = json.loads(Path(path).read_text())
    return [c for c in configs if not c.get("broken")]


def _port_from_url(base_url):
    m = re.search(r":(\d+)", base_url)
    return int(m.group(1)) if m else None


def _pid_comm(pid):
    try:
        out = subprocess.run(["ps", "-p", str(pid), "-o", "comm="],
                              capture_output=True, text=True, timeout=5)
        return out.stdout.strip().rsplit("/", 1)[-1]
    except Exception:
        return ""


def assert_serving_ready(base_url):
    """§3.5 bite 1: orchestrate.clear_port() SIGKILLs every llama-server on the stated
    premise that "we own the port exclusively" — false once llama-swap owns :8888 for daily
    use. Refuse to launch rather than silently eating someone's daily model server."""
    port = _port_from_url(base_url)
    if port is None:
        return
    for pid in lsof_listen_pids(port):
        comm = _pid_comm(pid)
        if comm.startswith("llama-swap"):
            sys.exit(
                f"ABORT: :{port} is held by llama-swap (pid {pid}, comm={comm!r}).\n"
                f"Run 'eval/harness/ops/serving_mode.sh eval' first to hand the port to the "
                f"eval harness, then re-run run_ifeval.py."
            )


# ---------------------------------------------------------------------------
# prompts (reuse evaluation_lib.read_prompt_list — do not reparse the jsonl ourselves)
# ---------------------------------------------------------------------------

def load_inputs(limit=None):
    inputs = evaluation_lib.read_prompt_list(str(DATA_PATH))
    return inputs[:limit] if limit else inputs


# ---------------------------------------------------------------------------
# generation
# ---------------------------------------------------------------------------

def strip_reasoning(message, mode):
    """Strip <think>/<reasoning>/<thinking> wrappers out of `content`. Confirmed empirically
    (see the module-level comment above REASONING_TAG_RE): this server has no separate
    reasoning_content/reasoning field, so "prefer the separate field" degrades to "there is no
    separate field" — reading one, if present on some other server, is still supported as a
    no-op signal (had_reasoning_field), but stripping content is the only real path here.

    mode == "off" -> no stripping at all (for measuring/confirming raw leakage).
    mode in ("auto", "on") -> both resolve to stripping (the leak is confirmed, not
    hypothetical); kept as two names for CLI clarity ("auto" = the recommended default).

    TRUNCATION: a thinking model can exhaust its whole `max_tokens` budget on reasoning and
    return finish_reason "length" with an OPENING <think> tag and no closing one — the entire
    visible `content` is then unterminated reasoning, never an answer. REASONING_TAG_RE cannot
    match an unclosed tag, so after the well-formed-pair pass, any leftover unclosed opening
    tag and everything after it is discarded too. This can and should yield an EMPTY string —
    that is correct (the model produced no answer within budget), not a bug to paper over; the
    caller must track it (`n_empty_after_strip`) rather than let it look like a silent miss.

    Returns (clean_content, was_stripped, had_reasoning_field, truncated).
    """
    content = message.get("content") or ""
    had_reasoning_field = bool(message.get("reasoning_content") or message.get("reasoning"))
    if mode == "off":
        return content, False, had_reasoning_field, False

    stripped = REASONING_TAG_RE.sub("", content)
    truncated = False
    open_match = OPEN_REASONING_TAG_RE.search(stripped)
    if open_match:  # a well-formed pass left an unclosed opening tag -> truncation
        stripped = stripped[:open_match.start()]
        truncated = True
    stripped = stripped.strip()
    was_stripped = truncated or (stripped != content.strip())
    return stripped, was_stripped, had_reasoning_field, truncated


def generate_one(client, base_url, key, model_id, prompt, strip_mode, max_tokens):
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    payload = {
        "model": model_id,
        # No system prompt: a system prompt would contaminate an instruction-following
        # measurement (IMPLEMENTATION_PLAN.md §5 point 2).
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "stream": False,
        **NEUTRAL_SAMPLING,
    }
    r = client.post(f"{base_url}/chat/completions", headers=headers, json=payload, timeout=600)
    r.raise_for_status()
    choice = r.json()["choices"][0]
    content, stripped, had_reasoning, truncated = strip_reasoning(choice.get("message", {}), strip_mode)
    return content, stripped, had_reasoning, truncated, choice.get("finish_reason")


def run_generation(config, base_url, key, limit, strip_mode, max_tokens):
    """Resumable per prompt: each successful/errored attempt is appended immediately, so a
    crash or usage-limit stop loses at most one in-flight prompt — same skip-if-done
    discipline as orchestrate.py's per-unit result files."""
    WORK_DIR.mkdir(parents=True, exist_ok=True)
    work_path = WORK_DIR / f"{config['model']}__{config['quant']}.jsonl"

    done_keys = set()
    if work_path.exists():
        for line in work_path.read_text().splitlines():
            if not line.strip():
                continue
            try:
                done_keys.add(json.loads(line)["key"])
            except (json.JSONDecodeError, KeyError):
                continue

    inputs = load_inputs(limit)
    pending = [inp for inp in inputs if inp.key not in done_keys]
    label = f"{config['model']}/{config['quant']}"
    if not pending:
        print(f"  [ifeval] {label}: all {len(inputs)} prompts already generated -> {work_path}")
        return work_path

    print(f"  [ifeval] {label}: {len(pending)}/{len(inputs)} prompts pending")
    with httpx.Client() as client, open(work_path, "a") as out_f:
        for i, inp in enumerate(pending, 1):
            t0 = time.monotonic()
            try:
                content, stripped, had_reasoning, truncated, finish_reason = generate_one(
                    client, base_url, key, config["opencode_model_id"], inp.prompt,
                    strip_mode, max_tokens,
                )
                record = {
                    "key": inp.key, "prompt": inp.prompt, "response": content,
                    "reasoning_stripped": stripped, "had_reasoning_field": had_reasoning,
                    "truncated": truncated, "finish_reason": finish_reason,
                    "wall_s": round(time.monotonic() - t0, 2), "ts": now_iso(), "error": None,
                }
                if truncated:
                    print(f"  [ifeval] {label}: prompt {inp.key} TRUNCATED "
                          f"(finish_reason={finish_reason!r}, unclosed reasoning tag) "
                          f"-> empty response is correct, not a bug")
            except Exception as e:  # noqa: BLE001 — record and move on, never abort the run
                record = {
                    "key": inp.key, "prompt": inp.prompt, "response": "",
                    "reasoning_stripped": False, "had_reasoning_field": False,
                    "truncated": False, "finish_reason": None,
                    "wall_s": round(time.monotonic() - t0, 2), "ts": now_iso(), "error": str(e),
                }
                print(f"  [ifeval] {label}: prompt {inp.key} ERROR: {e}")
            out_f.write(json.dumps(record) + "\n")
            out_f.flush()
            if i % 50 == 0:
                print(f"  [ifeval] {label}: {i}/{len(pending)} done")
    return work_path


def diagnostics(work_path):
    """One pass over the work jsonl for the counts that make a bad number legible instead of
    mysterious: a request error, a finish_reason=="length" truncation, and a response that
    came out empty after stripping (the two truncation gives are related but not identical —
    a "length" stop with a closed-enough tag could still leave a partial answer; this counts
    the case that actually zeroes out the scored response). Missing fields (e.g. a hand-built
    --score-only fixture with no finish_reason at all) default to falsy, never crash."""
    n_errors = n_finish_length = n_empty_after_strip = 0
    if not Path(work_path).exists():
        return {"n_errors": 0, "n_finish_length": 0, "n_empty_after_strip": 0}
    for line in Path(work_path).read_text().splitlines():
        if not line.strip():
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        if rec.get("error"):
            n_errors += 1
            continue
        if rec.get("finish_reason") == "length":
            n_finish_length += 1
        if not (rec.get("response") or "").strip():
            n_empty_after_strip += 1
    return {"n_errors": n_errors, "n_finish_length": n_finish_length,
            "n_empty_after_strip": n_empty_after_strip}


# ---------------------------------------------------------------------------
# scoring (imports evaluation_lib's strict/loose testers — never reimplemented)
# ---------------------------------------------------------------------------

def mean(xs):
    return round(sum(xs) / len(xs), 4) if xs else 0.0


def prompt_level(outputs):
    return mean([1.0 if o.follow_all_instructions else 0.0 for o in outputs])


def inst_level(outputs):
    flags = [f for o in outputs for f in o.follow_instruction_list]
    return mean([1.0 if f else 0.0 for f in flags])


def by_instruction_type(outputs):
    """Per full instruction id (e.g. "length_constraints:number_words"), computed on the
    strict metric — the headline is prompt_level_strict, so the breakdown matches it. This
    is the number that turns "qwen is bad at formats" into "qwen fails THESE format classes"
    (IMPLEMENTATION_PLAN.md §5)."""
    totals, corrects = {}, {}
    for o in outputs:
        for iid, followed in zip(o.instruction_id_list, o.follow_instruction_list):
            totals[iid] = totals.get(iid, 0) + 1
            corrects[iid] = corrects.get(iid, 0) + (1 if followed else 0)
    return {iid: round(corrects[iid] / totals[iid], 4) for iid in sorted(totals)}


def score_and_build(work_path, model, quant, base_url, strip_mode, max_tokens, limit, diag):
    inputs_all = load_inputs(limit)
    prompt_to_response = evaluation_lib.read_prompt_to_response_dict(str(work_path))
    inputs = [inp for inp in inputs_all if inp.prompt in prompt_to_response]
    if not inputs:
        sys.exit(f"no scored prompts: none of the prompts in {work_path} matched "
                  f"{DATA_PATH} — nothing to score")

    strict_outputs = [evaluation_lib.test_instruction_following_strict(inp, prompt_to_response)
                       for inp in inputs]
    loose_outputs = [evaluation_lib.test_instruction_following_loose(inp, prompt_to_response)
                      for inp in inputs]

    return {
        "benchmark": "ifeval",
        "model": model, "quant": quant,
        "n_prompts": len(inputs_all),
        "n_scored": len(inputs),
        "n_errors": diag["n_errors"],
        # Load-bearing, not decoration (same argument as BCB's n_env_errors): a thinking
        # config that never gets past reasoning within max_tokens will score near zero on
        # prompt_level_strict, and that must be a stated fact ("N/n_scored prompts truncated
        # before an answer"), not something inferred from a suspiciously bad number.
        "n_finish_length": diag["n_finish_length"],
        "n_empty_after_strip": diag["n_empty_after_strip"],
        "prompt_level_strict": prompt_level(strict_outputs),
        "inst_level_strict": inst_level(strict_outputs),
        "prompt_level_loose": prompt_level(loose_outputs),
        "inst_level_loose": inst_level(loose_outputs),
        "by_instruction_type": by_instruction_type(strict_outputs),
        "generation": {
            **NEUTRAL_SAMPLING,
            "max_tokens": max_tokens,
            "system_prompt": None,
            "endpoint": base_url,
            "reasoning_stripped": strip_mode != "off",
        },
        "vendor_sha": vendor_sha256(),
        "schema_version": 1,
        "ts": now_iso(),
    }


# ---------------------------------------------------------------------------
# per-config orchestration (serve/wait/unload imported from orchestrate.py)
# ---------------------------------------------------------------------------

def run_one_config(config, args, log_dir):
    label = f"{config['model']}/{config['quant']}"
    out_path = Path(args.out) if args.out else RESULTS_DIR / f"ifeval__{config['model']}__{config['quant']}.json"
    print(f"[ifeval] {label} -> {out_path}")

    log_path = log_dir / f"ifeval_serve__{config['serve_name']}.log"
    t0 = time.monotonic()
    proc, ready = serve_config(config, log_path)
    if not ready:
        print(f"  [ifeval] {label} FAILED to come up, skipping (see {log_path}). "
              f"Not touching configs.json's 'broken' flag — that's orchestrate.py's call.")
        unload(proc)
        return

    try:
        work_path = run_generation(config, args.base_url, orchestrate_api_key(),
                                    args.limit, args.strip_reasoning, args.max_tokens)
    finally:
        unload(proc)

    diag = diagnostics(work_path)
    result = score_and_build(work_path, config["model"], config["quant"], args.base_url,
                              args.strip_reasoning, args.max_tokens, args.limit, diag)
    result["wall_clock_s"] = round(time.monotonic() - t0, 1)
    atomic_write_json(out_path, result)
    print(f"  [ifeval] {label}: prompt_level_strict={result['prompt_level_strict']} "
          f"inst_level_strict={result['inst_level_strict']} "
          f"n_scored={result['n_scored']}/{result['n_prompts']} "
          f"n_errors={diag['n_errors']} n_finish_length={diag['n_finish_length']} "
          f"n_empty_after_strip={diag['n_empty_after_strip']}")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--only", default=None, help="filter configs.json entries by 'model' field")
    ap.add_argument("--limit", type=int, default=None, help="truncate the 541-prompt list (dev runs)")
    ap.add_argument("--out", default=None,
                    help="override the output path; only valid when exactly one config is selected")
    ap.add_argument("--base-url", default=API_BASE_DEFAULT)
    ap.add_argument("--configs", default=str(DEFAULT_CONFIGS_PATH))
    ap.add_argument("--max-tokens", type=int, default=MAX_TOKENS)
    ap.add_argument("--strip-reasoning", choices=["auto", "on", "off"], default="auto")
    ap.add_argument("--score-only", default=None,
                    help="score a saved generations jsonl offline (schema: {key,prompt,response,...}); "
                         "no server contact, no model needed")
    ap.add_argument("--model", default=None, help="model label for --score-only output naming")
    ap.add_argument("--quant", default=None, help="quant label for --score-only output naming")
    args = ap.parse_args()

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    if args.score_only:
        if not args.model or not args.quant:
            sys.exit("--score-only requires --model and --quant (for output naming/labeling)")
        out_path = Path(args.out) if args.out else RESULTS_DIR / f"ifeval__{args.model}__{args.quant}.json"
        work_path = Path(args.score_only)
        diag = diagnostics(work_path)
        t0 = time.monotonic()
        result = score_and_build(work_path, args.model, args.quant, args.base_url,
                                  args.strip_reasoning, args.max_tokens, args.limit, diag)
        result["wall_clock_s"] = round(time.monotonic() - t0, 2)
        atomic_write_json(out_path, result)
        print(f"[ifeval] score-only wrote {out_path}")
        print(f"  prompt_level_strict={result['prompt_level_strict']} "
              f"inst_level_strict={result['inst_level_strict']} "
              f"prompt_level_loose={result['prompt_level_loose']} "
              f"inst_level_loose={result['inst_level_loose']}")
        return

    configs = load_configs(args.configs)
    if args.only:
        configs = [c for c in configs if c["model"] == args.only]
    if not configs:
        sys.exit(f"no non-broken configs matched --only {args.only!r} in {args.configs}")
    if args.out and len(configs) != 1:
        sys.exit(f"--out only valid when exactly one config is selected "
                  f"({len(configs)} matched --only {args.only!r}); narrow --only or drop --out")

    assert_serving_ready(args.base_url)

    log_dir = RESULTS_DIR / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    for config in configs:
        run_one_config(config, args, log_dir)


if __name__ == "__main__":
    main()
