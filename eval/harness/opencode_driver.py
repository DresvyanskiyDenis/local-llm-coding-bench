# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""opencode_driver.py — runs ONE (task x model) attempt through headless OpenCode (see
CONTRACT.md §3). Sets up the model's working dir (suite-aware, see below), runs
`opencode run "<PROMPT.md>" --model <id> --agent <agent> --auto`, captures the session
id from the streamed JSON events, exports the full transcript, derives per-turn timing/
token/tool-call metrics from it, and writes driver.json. The driver does NOT grade.

Working-dir setup (confirmed live against the landed tasks/ tree, 2026-07-12): A_coding/
B_review/C_edit tasks all ship a repo/ that gets copied as the cwd, unchanged. D_text
has no repo/ -- D1 ships source/ (e.g. doc.md) instead, which gets copied into the cwd;
D2 ships neither, so the cwd is a fresh empty dir. All three cases land at the same
rundir/repo path (driver.json's repo_dir field stays populated either way -- it's just
"the model's working directory", not necessarily a copy of a repo/). D's entrypoint is
null and its grader is "judge" (Opus-adjudicated later); this driver doesn't grade, so
that only affects orchestrate.py/graders, not this file -- answer.txt is captured the
same way for every suite.

High-effort knob (verified live 2026-07-12, see effort_knob in the output and the
return message): `opencode run --variant <effort>` — documented in `opencode run --help`
as "model variant (provider-specific reasoning effort)". A live sanity run against the
served `qwen` model confirmed via `opencode export` that the session recorded
`info.model.variant == "high"`. OpenCode only auto-generates that variant for a model
that declares `"reasoning": true` in opencode.json, so this driver looks that flag up
live (provider.unsloth-studio.models.<bare-id>.reasoning) and only passes --variant when
it's set — this is the "per-config reasoning hint" PLAN §10.3 asks for, read from the
same file the fleet is served from rather than a new CLI flag (the orchestrator's fixed
call, see CONTRACT §3, has no slot for one). Binary-reasoning GGUFs (Qwen3.6/GLM/Gemma-4/
qwen27 family) already have thinking forced ON at the unsloth-serve launch flags
(--reasoning on) since llama.cpp has no graduated low/medium/high for them; gpt-oss gets
a real graduated Harmony reasoning_effort. KAT-Dev (--reasoning off, deliberately
non-thinking) and North Mini (no reasoning flag declared, thinking status unverified)
are left un-forced.

Usage:
    uv run opencode_driver.py --task tasks/A_coding/A1_events_transform \\
        --model unsloth/Qwen3.6-35B-A3B-MTP-GGUF --agent build \\
        --run runs/qwen__q5__A_coding__A1__rep1 --effort high --timeout 900 \\
        --out runs/qwen__q5__A_coding__A1__rep1/driver.json
"""

import argparse
import json
import os
import re
import shutil
import signal
import subprocess
import time
from pathlib import Path

DEFAULT_OPENCODE_CONFIG = Path.home() / ".config/opencode/opencode.json"
PROVIDER = "unsloth-studio"
EXPORT_TIMEOUT_S = 60
LOOP_TURN_THRESHOLD = 40  # best-effort: sessions this long get flagged infinite_loop

XML_LEAK_PATTERNS = [
    re.compile(r"<tool_call>", re.I),
    re.compile(r"</tool_call>", re.I),
    re.compile(r"<\|channel\|>"),
    re.compile(r"<function_call>", re.I),
]


def resolve_model_ids(raw_model):
    """--model may arrive bare ("unsloth/Qwen3.6-...") — what configs.json/orchestrate.py
    actually pass — or already carry the provider prefix. Return (full_id_for_opencode_run,
    bare_id_for_opencode_json_lookup)."""
    if "/" in raw_model and raw_model.split("/", 1)[0] == PROVIDER:
        return raw_model, raw_model[len(PROVIDER) + 1:]
    return f"{PROVIDER}/{raw_model}", raw_model


def model_reasoning_enabled(bare_model_id, config_path):
    try:
        cfg = json.loads(Path(config_path).read_text())
        models = cfg["provider"][PROVIDER]["models"]
        return bool(models.get(bare_model_id, {}).get("reasoning", False))
    except Exception:
        return False


def atomic_write_json(path, data):
    path = Path(path)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2))
    tmp.replace(path)


def run_opencode(prompt_text, full_model_id, agent, effort, pass_variant, repo_dir, rundir,
                  timeout_s, opencode_bin):
    # --dir is required, not just cwd: verified live 2026-07-12 that `opencode run` under
    # a plain subprocess cwd= silently ran against an unrelated, previously-used project
    # directory (its own last-project state) instead of the repo copy -- --dir pins it.
    cmd = [opencode_bin, "run", prompt_text, "--model", full_model_id, "--agent", agent,
           "--auto", "--format", "json", "--dir", str(repo_dir)]
    if pass_variant:
        cmd += ["--variant", effort]

    stdout_path = rundir / "_opencode_stdout.jsonl"
    stderr_path = rundir / "_opencode_stderr.log"
    t0 = time.monotonic()
    timed_out = False
    with open(stdout_path, "wb") as out_f, open(stderr_path, "wb") as err_f:
        proc = subprocess.Popen(cmd, cwd=repo_dir, stdout=out_f, stderr=err_f,
                                 start_new_session=True)
        try:
            proc.wait(timeout=timeout_s)
        except subprocess.TimeoutExpired:
            timed_out = True
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                proc.wait(timeout=10)
            except ProcessLookupError:
                pass
    wall_s = round(time.monotonic() - t0, 2)
    returncode = proc.returncode

    session_id = None
    for line in stdout_path.read_text(errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        sid = event.get("sessionID")
        if sid:
            session_id = sid
            break
    return session_id, timed_out, returncode, wall_s, cmd


def export_session(session_id, opencode_bin):
    try:
        result = subprocess.run([opencode_bin, "export", session_id], capture_output=True,
                                 text=True, timeout=EXPORT_TIMEOUT_S)
    except subprocess.TimeoutExpired:
        return None, "export timed out"
    if result.returncode != 0:
        return None, f"export failed: {result.stderr[:500]}"
    return result.stdout, None


def analyze_transcript(transcript):
    """Derive driver.json's export-sourced fields from one `opencode export` payload
    (schema confirmed live 2026-07-12): {"info": {...}, "messages": [{"info": {...},
    "parts": [...]}, ...]}. Each assistant message == one agent turn/step; its
    info.tokens.{input,output,reasoning,cache.read,cache.write} are that turn's own
    counts (not cumulative)."""
    messages = transcript.get("messages", [])
    assistant_msgs = [m for m in messages if m.get("info", {}).get("role") == "assistant"]
    turns = len(assistant_msgs)

    think_tokens = answer_tokens = prompt_total = 0
    reasoning_chars = 0  # fallback proxy -- see note below
    tool_calls_total = tool_calls_malformed = 0
    xml_leak = False
    ttft_ms_per_turn, decode_tps_per_turn = [], []
    final_text_parts = []

    for m in assistant_msgs:
        info = m.get("info", {})
        tokens = info.get("tokens", {}) or {}
        cache = tokens.get("cache", {}) or {}
        think_tokens += tokens.get("reasoning") or 0
        out_tok = tokens.get("output") or 0
        answer_tokens += out_tok
        prompt_total += (tokens.get("input") or 0) + (cache.get("read") or 0) + (cache.get("write") or 0)

        created = (info.get("time") or {}).get("created")
        completed = (info.get("time") or {}).get("completed")
        parts = m.get("parts", [])
        first_part_start = None
        for p in parts:
            t = p.get("time") or {}
            if t.get("start") is not None and (first_part_start is None or t["start"] < first_part_start):
                first_part_start = t["start"]
            if p.get("type") == "tool":
                tool_calls_total += 1
                if (p.get("state") or {}).get("status") == "error":
                    tool_calls_malformed += 1
            if p.get("type") == "text" and any(pat.search(p.get("text", "")) for pat in XML_LEAK_PATTERNS):
                xml_leak = True
                tool_calls_malformed += 1
            if p.get("type") == "reasoning":
                reasoning_chars += len(p.get("text", "") or "")

        if created is not None and first_part_start is not None:
            ttft_ms_per_turn.append(round(first_part_start - created, 1))
            if completed is not None and out_tok > 1:
                decode_span_s = (completed - first_part_start) / 1000.0
                decode_tps_per_turn.append(round((out_tok - 1) / decode_span_s, 1) if decode_span_s > 0 else None)
            else:
                decode_tps_per_turn.append(None)
        else:
            ttft_ms_per_turn.append(None)
            decode_tps_per_turn.append(None)

    if assistant_msgs:
        final_text_parts = [p.get("text", "") for p in assistant_msgs[-1].get("parts", []) if p.get("type") == "text"]
    final_answer = "\n".join(t for t in final_text_parts if t).strip()

    # Verified live 2026-07-12: Unsloth Studio's usage payload reports tokens.reasoning=0
    # even when a message has a populated "reasoning"-type part with real thinking text
    # (the server doesn't count it separately). Fall back to a ~4-chars/token estimate
    # from the visible reasoning text so metric #12 (think:answer ratio) isn't silently
    # zeroed for every thinking model.
    if think_tokens == 0 and reasoning_chars > 0:
        think_tokens = round(reasoning_chars / 4)

    think_answer_ratio = round(think_tokens / answer_tokens, 3) if answer_tokens else None

    return {
        "turns": turns,
        "ttft_ms_per_turn": ttft_ms_per_turn,
        "decode_tps_per_turn": decode_tps_per_turn,
        "tokens": {"think": think_tokens, "answer": answer_tokens, "prompt_total": prompt_total},
        "think_answer_ratio": think_answer_ratio,
        "tool_calls": {"total": tool_calls_total, "malformed": tool_calls_malformed},
        "xml_leak": xml_leak,
        "final_answer": final_answer,
    }


def classify(timed_out, returncode, analysis):
    """termination: clean|hit_timeout|no_tools|xml_leak|loop (CONTRACT §3).
    status: completed|timeout|error|stalled|infinite_loop."""
    turns = analysis["turns"] if analysis else 0
    if timed_out:
        termination = "hit_timeout"
    elif analysis is None:
        termination = None
    elif analysis["xml_leak"]:
        termination = "xml_leak"
    elif analysis["tool_calls"]["total"] == 0:
        termination = "no_tools"
    elif turns >= LOOP_TURN_THRESHOLD:
        termination = "loop"
    else:
        termination = "clean"

    if timed_out:
        status = "timeout"
    elif returncode != 0:
        status = "error"
    elif termination == "loop":
        status = "infinite_loop"
    elif turns == 0:
        status = "stalled"
    else:
        status = "completed"
    return status, termination


def build_effort_knob(effort, pass_variant):
    applied = (f"--variant {effort} passed (model declares reasoning:true in opencode.json)"
               if pass_variant else
               "--variant omitted (model has no reasoning:true capability declared in "
               "opencode.json -- e.g. KAT-Dev's deliberate --reasoning off, or North Mini's "
               "unverified thinking status; effort is governed by the unsloth-serve launch "
               "flags only for this model)")
    return (
        "opencode run --variant <effort> -- verified 2026-07-12: `opencode run --help` "
        "documents --variant as 'model variant (provider-specific reasoning effort, e.g. "
        "high, max, minimal)'; a live sanity run (qwen, --variant high) confirmed via "
        "`opencode export` that the session's info.model.variant == 'high'. OpenCode "
        "auto-generates a default variant for any model with reasoning:true in "
        "opencode.json, mapped to reasoningEffort=high on the openai-compatible provider; "
        "binary-reasoning GGUFs (Qwen3.6/GLM/Gemma-4/qwen27) already have thinking forced "
        "ON at the unsloth-serve launch flags (--reasoning on) since llama.cpp has no "
        "graduated level for them, gpt-oss gets a real graduated Harmony reasoning_effort. "
        "This run: " + applied
    )


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--task", required=True)
    ap.add_argument("--model", required=True, help="opencode-model-id, bare or provider-prefixed")
    ap.add_argument("--agent", required=True)
    ap.add_argument("--run", required=True, dest="rundir")
    ap.add_argument("--effort", default="high")
    ap.add_argument("--timeout", type=int, required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--opencode-config", default=str(DEFAULT_OPENCODE_CONFIG),
                     help="for the reasoning-capability lookup; override in tests")
    ap.add_argument("--opencode-bin", default="opencode", help="override for testing")
    args = ap.parse_args()

    task_dir = Path(args.task)
    rundir = Path(args.rundir)
    rundir.mkdir(parents=True, exist_ok=True)

    repo_src = task_dir / "repo"
    source_src = task_dir / "source"
    repo_dst = rundir / "repo"
    if repo_dst.exists():
        shutil.rmtree(repo_dst)
    if repo_src.exists():
        shutil.copytree(repo_src, repo_dst)
    elif source_src.exists():
        shutil.copytree(source_src, repo_dst)
    else:
        repo_dst.mkdir(parents=True)

    prompt_text = (task_dir / "PROMPT.md").read_text()
    full_model_id, bare_model_id = resolve_model_ids(args.model)
    pass_variant = model_reasoning_enabled(bare_model_id, args.opencode_config)

    session_id, timed_out, returncode, wall_s, cmd = run_opencode(
        prompt_text, full_model_id, args.agent, args.effort, pass_variant,
        repo_dst, rundir, args.timeout, args.opencode_bin,
    )

    transcript_path = rundir / "transcript.json"
    analysis = None
    if session_id:
        raw, err = export_session(session_id, args.opencode_bin)
        if raw is not None:
            transcript_path.write_text(raw)
            try:
                analysis = analyze_transcript(json.loads(raw))
            except json.JSONDecodeError:
                analysis = None
        else:
            transcript_path.write_text(json.dumps({"error": err}))
    else:
        transcript_path.write_text(json.dumps({"error": "no session id captured from opencode run"}))

    answer_path = rundir / "answer.txt"
    answer_path.write_text((analysis or {}).get("final_answer", "") or "")

    status, termination = classify(timed_out, returncode, analysis)

    driver_json = {
        "unit_partial": {"model": bare_model_id, "agent": args.agent, "effort": args.effort},
        "effort_knob": build_effort_knob(args.effort, pass_variant),
        "status": status,
        "turns": analysis["turns"] if analysis else None,
        "wall_s": wall_s,
        "ttft_ms_per_turn": analysis["ttft_ms_per_turn"] if analysis else None,
        "decode_tps_per_turn": analysis["decode_tps_per_turn"] if analysis else None,
        "tokens": analysis["tokens"] if analysis else None,
        "think_answer_ratio": analysis["think_answer_ratio"] if analysis else None,
        "tool_calls": analysis["tool_calls"] if analysis else None,
        "termination": termination,
        "session_id": session_id,
        "repo_dir": str(repo_dst),
        "answer_file": str(answer_path),
    }
    atomic_write_json(args.out, driver_json)
    print(json.dumps(driver_json, indent=2))


if __name__ == "__main__":
    main()
