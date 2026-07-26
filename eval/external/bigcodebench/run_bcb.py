# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "httpx>=0.27",   # not used directly: orchestrate.py imports it at module level
# ]
# ///
"""BigCodeBench-Hard (instruct) across the local fleet: generate -> evaluate -> normalize.

    uv run eval/external/bigcodebench/run_bcb.py --only opus --limit 10
    uv run eval/external/bigcodebench/run_bcb.py                    # all non-broken configs
    uv run eval/external/bigcodebench/run_bcb.py --dry-run          # print commands, run nothing

WHAT THIS IS AND IS NOT COMPARABLE TO
    Executed with RELAXED PINS and BigCodeBench's LOCAL executor (`--execution local`), because
    requirements-eval.txt pins numpy==1.21.2 / numba==0.55.0 / keras==2.11.0 / tensorflow==2.11.0,
    none of which have Apple-Silicon wheels, and because Docker/Rosetta was rejected on RAM
    grounds (36 GB unified is already binding with a 35B GGUF resident) — IMPLEMENTATION_PLAN.md
    §1 and §10.1. Every config runs under the IDENTICAL executor, so the within-fleet RANKING
    (which is what the Spearman correlation needs) holds. The absolute pass@1 does NOT transfer:
    it is not comparable to the public BigCodeBench leaderboard, and the result JSON says so in
    its `comparability` field.

FOUR THINGS THIS SCRIPT REFUSES TO DO IMPLICITLY
 1. It will not kill llama-swap. If :8888 is held by llama-swap the run aborts and names
    `eval/harness/ops/serving_mode.sh eval`. (orchestrate.clear_port() now guards this too;
    the assert is repeated here so the failure lands before a model is ever launched.)
 2. It will not talk to :8888 directly. Generation goes through eval_proxy.py on :8899, which
    is the ONLY place the neutral sampling block can be injected: BigCodeBench's client accepts
    just max_tokens/temperature/reasoning_effort/n (gen/util/openai_request.py:7-14) and
    hardcodes top_p=0.95, so top_k / min_p / presence_penalty fall through to per-model server
    defaults — and those differ across the fleet (sampler-coder carries --presence-penalty 1.5).
 3. It will not grade completions it did not generate. `--resume` must stay on BigCodeBench's
    own command line (generate.py:216 does a bare `os.remove(target_path)` when resume is off,
    which raises FileNotFoundError on the first run of a config), so freshness is enforced HERE
    instead: any pre-existing samples file is moved aside before generation unless --resume was
    asked for explicitly. MEASURED 2026-07-26: without that, a rerun skipped all 10 tasks in
    23.6 s and wrote an artifact that asserted neutral sampling with n_proxy_requests == 0 — it
    had graded the previous day's completions. `generation.completions_provenance` now states,
    in every artifact, whether the scored completions came from this run's proxy or off disk.
 4. It will not report a bare pass@1. `n_no_program` (empty or unparseable generations) and
    `n_env_errors` (tasks whose own ground truth fails here) are derived from the artifacts,
    never assumed: without them a truncation bug or a missing numba is indistinguishable from
    a model that genuinely failed the task. Note `sanitize()` returns prose VERBATIM when it
    finds no code, so emptiness alone detects nothing — see completion_stats().

UPSTREAM BEHAVIOURS WORKED AROUND (all verified against the installed 0.2.5 source)
  * generate.py's batching flushes to disk only when `bs` is reached or the dataset ends
    (generate.py:88). With the default bs=None a 148-task run writes NOTHING until the very
    end, and --resume then has nothing to resume from. We pass --bs 1: one task, one flush.
  * evaluate.py asserts `len(completion_id) == len(problems)` (evaluate.py:322) — the samples
    file must cover every task in the problem set. So --limit is implemented as
    `--id-range 0-N` on generate PLUS `--selective-evaluate <the ids actually generated>` on
    evaluate, rather than by hand-editing the samples file.
  * evaluate.py calls input() if eval_results.json / pass_at_k.json already exist
    (evaluate.py:400,420). Stale artifacts are renamed aside first and stdin is /dev/null, so a
    scripted run can never block on a prompt nobody is there to answer.
  * make_auto_request retries FOREVER on any exception (gen/util/openai_request.py:35). A dead
    endpoint would spin silently, so both subprocesses run under an explicit timeout.
  * --pass-k is deliberately NOT passed: fire would coerce "1" to int and evaluate.py then
    iterates it (evaluate.py:218). The default "1,5,10" already yields only pass@1 for
    n_samples=1, since higher k are skipped when total.min() < k.
  * --max-as-limit 0 --max-data-limit 0 --max-stack-limit 0 — see RLIMIT_NOTE below. Without
    this, EVERY task on this machine fails inside reliability_guard before its test body runs.
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import shutil
import signal
import socket
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


HERE = Path(__file__).resolve().parent
EVAL_DIR = HERE.parent.parent  # eval/
HARNESS_DIR = EVAL_DIR / "harness"
RESULTS_DIR = EVAL_DIR / "results"
GEN_DIR = HERE / "_gen"  # gitignored
VENV_PY = HERE / ".venv" / "bin" / "python"
ENV_HEALTH = HERE / "env_health.json"
EVAL_PROXY = HARNESS_DIR / "eval_proxy.py"
SERVING_MODE = HARNESS_DIR / "ops" / "serving_mode.sh"

BCB_VERSION = "0.2.5"
# 2: generation.reasoning_stripped went from a bool echoing the CLI flag to a dict reporting
#    what the proxy actually observed, and generation.completions_provenance was added.
SCHEMA_VERSION = 2
SPLIT = "instruct"
SUBSET = "hard"
N_HARD_TASKS = 148
MAX_NEW_TOKENS = (
    4096  # NOT the 1280 default: thinking models blow that budget mid-solution
)
# and the sanitizer then sees a truncated program.
PROXY_PORT = 8899
GEN_TIMEOUT_S = 6 * 60 * 60
EVAL_TIMEOUT_S = 3 * 60 * 60
EVAL_EXIT_GRACE_S = (
    120  # after evaluate writes its results but before we stop waiting for it
)
# to exit; see wait_for_evaluate() for why it may never exit.
EVAL_PARALLEL = 4  # BCB's default is cpu_count()//2; with rlimits off (below) an
# unbounded worker is a memory risk, and this box serves a 35B GGUF.

# MEASURED 2026-07-25, Darwin arm64 / CPython 3.12.13: resource.setrlimit(RLIMIT_AS, v) and
# (RLIMIT_DATA, v) raise ValueError "current limit exceeds maximum limit" for EVERY v tried
# (64 MB .. 30 GB), inside and outside the agent sandbox. reliability_guard applies both
# unconditionally (eval/utils.py:301-311), so under BigCodeBench's defaults the guard raises
# before any test body runs: a first ground-truth run logged 80 such errors in ~90 tasks.
# That would have produced pass@1 == 0 for every config, indistinguishable from genuine
# model failure — the exact confusion n_env_errors exists to prevent.
# The guard is gated on `if max_as_limit and max_data_limit and max_stack_limit:`, so 0
# skips the rlimit block only, leaving TZ pinning / faulthandler / builtins hardening intact.
# Vendored code is NOT modified. Recorded in every result JSON under executor.rlimits.
RLIMIT_FLAGS = [
    "--max-as-limit",
    "0",
    "--max-data-limit",
    "0",
    "--max-stack-limit",
    "0",
]
RLIMIT_NOTE = (
    "disabled: macOS setrlimit(RLIMIT_AS/RLIMIT_DATA) returns EINVAL at any value, "
    "so BigCodeBench's default 30 GB caps make every task fail in reliability_guard "
    "before its test runs"
)

sys.path.insert(0, str(HARNESS_DIR))
# orchestrate.py is import-safe (everything is behind `if __name__ == "__main__"`). The serve
# lifecycle is imported, never reimplemented — it survived three nights of real runs.
import orchestrate  # noqa: E402


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def log(msg: str) -> None:
    print(msg, flush=True)


def atomic_write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2) + "\n")
    tmp.replace(path)


# ---------------------------------------------------------------------------
# preflight
# ---------------------------------------------------------------------------


def assert_not_llama_swap(port: int = 8888) -> None:
    """Abort if :8888 belongs to llama-swap (IMPLEMENTATION_PLAN.md §3.5 bite 1).

    Uses orchestrate's helper when present so there is one definition of "is this llama-swap";
    falls back to a local lsof+ps check otherwise, because this assert must exist here
    regardless of what has landed in orchestrate.py.
    """
    listeners = None
    helper = getattr(orchestrate, "llama_swap_listeners", None)
    if callable(helper):
        listeners = helper(port)
    else:
        listeners = []
        for pid in orchestrate.lsof_listen_pids(port):
            cmd = subprocess.run(
                ["ps", "-p", str(pid), "-o", "command="], capture_output=True, text=True
            ).stdout.strip()
            if "llama-swap" in cmd:
                listeners.append((pid, cmd))
    if listeners:
        pid, cmd = listeners[0]
        raise SystemExit(
            f"ABORT: :{port} is held by llama-swap (pid {pid}: {cmd}), not by an eval server.\n"
            "Killing it would take OpenCode's daily fleet down. Flip the machine into eval\n"
            f"mode first:\n    {SERVING_MODE} eval\n"
            f"and restore it afterwards with:\n    {SERVING_MODE} daily"
        )


def upstream_is_harness_port(base_url: str) -> bool:
    return f":{orchestrate.PORT}" in base_url


def preflight(dry_run: bool, base_url: str) -> None:
    missing = []
    if not VENV_PY.exists():
        missing.append(f"{VENV_PY} (run: bash {HERE / 'bootstrap.sh'})")
    if not EVAL_PROXY.exists():
        missing.append(f"{EVAL_PROXY} (owned by the harness lane)")
    if missing:
        raise SystemExit("ABORT: missing prerequisites:\n  - " + "\n  - ".join(missing))
    if not ENV_HEALTH.exists():
        log(
            f"  WARNING: {ENV_HEALTH.name} not found — run env_health.py so n_env_errors has a "
            "baseline to be read against."
        )
    # Asserted whenever the upstream IS the harness port, even under --no-serve: an operator
    # who points at :8888 while llama-swap owns it would silently measure llama-swap's
    # per-model sampler defaults instead of the eval stack.
    if not dry_run and upstream_is_harness_port(base_url):
        assert_not_llama_swap(orchestrate.PORT)


# ---------------------------------------------------------------------------
# eval_proxy lifecycle
# ---------------------------------------------------------------------------


def port_open(port: int, host: str = "127.0.0.1", timeout: float = 0.5) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def start_proxy(upstream: str, port: int, log_path: Path, strip_reasoning: bool):
    """Start eval_proxy.py and wait until it accepts connections. Returns (proc, cmd)."""
    if port_open(port):
        raise SystemExit(
            f"ABORT: something is already listening on :{port}. eval_proxy needs it exclusively; "
            "a stale proxy from a crashed run would silently apply the wrong flags."
        )
    cmd = [
        "uv",
        "run",
        str(EVAL_PROXY),
        "--port",
        str(port),
        "--upstream",
        upstream,
        "--log",
        str(log_path),
    ]
    # eval_proxy.py's OWN default is --strip-reasoning=True (BooleanOptionalAction). Pass the
    # flag explicitly either way so the result JSON's "reasoning_stripped" field — which just
    # echoes this argument back — always matches what the proxy actually enforced, instead of
    # silently reporting False whenever this script's own --strip-reasoning wasn't passed.
    cmd.append("--strip-reasoning" if strip_reasoning else "--no-strip-reasoning")
    log(f"  [proxy] {' '.join(cmd)}")
    proc = subprocess.Popen(cmd, start_new_session=True)
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        if port_open(port):
            log(f"  [proxy] listening on :{port} -> {upstream}")
            return proc, cmd
        if proc.poll() is not None:
            raise SystemExit(
                f"ABORT: eval_proxy exited immediately (rc={proc.returncode})"
            )
        time.sleep(0.5)
    stop_proxy(proc)
    raise SystemExit(f"ABORT: eval_proxy never bound :{port} within 60s")


def stop_proxy(proc) -> None:
    if proc is None or proc.poll() is not None:
        return
    try:
        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
    except (ProcessLookupError, PermissionError):
        pass
    try:
        proc.wait(timeout=15)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            pass


def read_proxy_log(path: Path) -> tuple[dict, dict]:
    """(sampling block the proxy enforced, per-response stats derived from its log).

    finish_reason is NOT in BigCodeBench's artifacts: generate.py writes only
    {task_id, solution, raw_solution} (generate.py:107-112). The proxy is the only place it is
    observable, and it logs it ONLY for choices that stripping left empty
    (eval_proxy.py:186-188) -- which is exactly the case that matters: an unclosed <think>
    means the whole token budget went to reasoning. So `finish_reasons_on_empty["length"]` is
    the measured truncation count; a total finish_reason histogram is NOT available and is
    reported as such rather than silently omitted.
    """
    enforced = {}
    stats = {
        "n_requests": 0,
        "n_reasoning_stripped_choices": 0,
        "n_empty_after_strip": 0,
        "finish_reasons_on_empty": {},
        "finish_reason_coverage": (
            "empty-after-strip choices only; BCB's own artifacts "
            "preserve no finish_reason at all"
        ),
    }
    if not path.exists():
        return enforced, stats
    for line in path.read_text().splitlines():
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        if "enforced" not in rec:
            continue
        enforced = rec["enforced"]
        stats["n_requests"] += 1
        stats["n_reasoning_stripped_choices"] += (
            rec.get("reasoning_stripped_choices") or 0
        )
        stats["n_empty_after_strip"] += rec.get("empty_after_strip") or 0
        for fr in rec.get("empty_finish_reasons") or []:
            key = str(fr)
            stats["finish_reasons_on_empty"][key] = (
                stats["finish_reasons_on_empty"].get(key, 0) + 1
            )
    return enforced, stats


# ---------------------------------------------------------------------------
# bigcodebench invocation
# ---------------------------------------------------------------------------


def samples_path_for(root: Path, model_id: str) -> Path:
    """The path generate.py builds (generate.py:206) — recomputed, then verified by glob.

    identifier = model.replace('/','--') + f'--{revision}--bigcodebench{extra}-{split}--'
                 f'{backend}-{temperature}-{n_samples}-sanitized_calibrated.jsonl'
    with revision='main', extra='-hard', backend='openai', temperature=0, n_samples=1.
    """
    ident = (
        f"{model_id.replace('/', '--')}--main--bigcodebench-{SUBSET}-{SPLIT}"
        f"--openai-0-1-sanitized_calibrated.jsonl"
    )
    return root / ident


def resolve_samples(root: Path, model_id: str) -> Path | None:
    expected = samples_path_for(root, model_id)
    if expected.exists():
        return expected
    candidates = [p for p in root.glob("*.jsonl") if "sanitized" in p.name]
    if len(candidates) == 1:
        log(
            f"  NOTE: expected {expected.name} but found {candidates[0].name}; using it."
        )
        return candidates[0]
    return None


def run_generate(
    model_id: str,
    root: Path,
    base_url: str,
    limit: int | None,
    env: dict,
    dry_run: bool,
) -> tuple[Path | None, float, str]:
    root.mkdir(parents=True, exist_ok=True)
    cmd = [
        str(VENV_PY),
        "-m",
        "bigcodebench.generate",
        "--model",
        model_id,
        "--backend",
        "openai",
        "--base-url",
        base_url,
        "--split",
        SPLIT,
        "--subset",
        SUBSET,
        "--greedy",
        "--resume",
        "--max-new-tokens",
        str(MAX_NEW_TOKENS),
        "--bs",
        "1",  # flush per task; see module docstring
        "--root",
        str(root),
    ]
    if limit:
        cmd += ["--id-range", f"0-{limit}"]
    printable = " ".join(cmd)
    log(f"  [generate] {printable}")
    if dry_run:
        return None, 0.0, printable
    t0 = time.monotonic()
    rc = subprocess.run(
        cmd, env=env, cwd=str(HERE), stdin=subprocess.DEVNULL, timeout=GEN_TIMEOUT_S
    ).returncode
    dt = time.monotonic() - t0
    if rc != 0:
        log(f"  [generate] FAILED rc={rc} after {dt:.0f}s")
        return None, dt, printable
    return resolve_samples(root, model_id), dt, printable


def stash_stale(path: Path) -> None:
    """Move an artifact aside under a UTC-stamped name. Never deletes.

    Two callers, one rule — nothing from an earlier run may be read by this one:
      * evaluate.py prompts on stdin when its output files already exist;
      * generate.py's --resume reads the samples file and skips every task it finds.
    """
    if path.exists():
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        dest = path.with_suffix(path.suffix + f".stale-{stamp}")
        shutil.move(str(path), str(dest))
        log(f"  [stash] moved stale {path.name} -> {dest.name}")


def stash_previous_generations(root: Path) -> int:
    """Move any samples file from an earlier run aside, so --resume finds nothing.

    `--resume` cannot simply be dropped: generate.py:216 runs a bare
    `os.remove(target_path)` when resume is False, which raises FileNotFoundError the first
    time a config is generated. So resume stays ON at BCB's level and freshness is enforced
    here. Globbed rather than name-computed: a samples file written under a different
    identifier (a renamed model id, a --skip-prefill run) must not survive either.
    """
    n = 0
    for stale in sorted(root.glob("*sanitized*.jsonl")):
        stash_stale(stale)
        n += 1
    return n


# Runs inside the BCB venv (this script's own interpreter has no bigcodebench).
GT_CACHE_GUARD = """
import os, pickle, sys
from bigcodebench.data import get_bigcodebench_hash
from bigcodebench.data.utils import CACHE_DIR
subset, wanted = sys.argv[1], set(sys.argv[2:])
cache = os.path.join(CACHE_DIR, get_bigcodebench_hash(subset=subset) + ".pkl")
if not os.path.exists(cache):
    print("no cache yet; ground truth will be computed")
else:
    try:
        have = set(pickle.load(open(cache, "rb")))
    except Exception as exc:
        have = set()
        print("unreadable cache (%s); removing" % type(exc).__name__)
    missing = wanted - have
    if missing:
        os.remove(cache)
        print("cache covers %d tasks, missing %d -> removed, will recompute"
              % (len(have), len(missing)))
    else:
        print("cache covers all %d requested tasks" % len(wanted))
"""


def ensure_gt_cache(task_ids: list[str]) -> None:
    """Delete BigCodeBench's ground-truth cache when it does not cover the tasks we evaluate.

    UPSTREAM TRAP: get_groundtruth() keys its pickle cache on the DATASET hash alone
    (evaluate.py:41) but computes it over the *filtered* problem set. So a `--limit 10` run
    writes a 10-entry cache under the full-subset key, and the next FULL run loads it and dies
    on `expected_time[task_id]` (evaluate.py:308) with a KeyError for the other 138 tasks —
    after generation has already been paid for. Cheap to check, expensive to discover at 3 a.m.
    """
    proc = subprocess.run(
        [str(VENV_PY), "-c", GT_CACHE_GUARD, SUBSET, *task_ids],
        capture_output=True,
        text=True,
    )
    for line in (proc.stdout or "").splitlines():
        log(f"  [gt-cache] {line}")
    if proc.returncode != 0:
        log(
            f"  [gt-cache] check failed (non-fatal): {(proc.stderr or '').strip()[:200]}"
        )


def run_evaluate(
    samples: Path, task_ids: list[str], limited: bool, dry_run: bool
) -> tuple[bool, float, str]:
    eval_results = Path(str(samples).replace(".jsonl", "_eval_results.json"))
    pass_at_k = Path(str(samples).replace(".jsonl", "_pass_at_k.json"))
    cmd = [
        str(VENV_PY),
        "-m",
        "bigcodebench.evaluate",
        "--split",
        SPLIT,
        "--subset",
        SUBSET,
        "--execution",
        "local",
        "--samples",
        str(samples),
        "--parallel",
        str(EVAL_PARALLEL),
        *RLIMIT_FLAGS,
    ]
    if limited:
        # required: evaluate asserts the samples cover every problem in the (filtered) set
        cmd += ["--selective-evaluate", ",".join(task_ids)]
    printable = " ".join(cmd)
    log(f"  [evaluate] {printable}")
    if dry_run:
        return False, 0.0, printable
    ensure_gt_cache(task_ids)
    stash_stale(eval_results)
    stash_stale(pass_at_k)
    t0 = time.monotonic()
    ok = wait_for_evaluate(cmd, pass_at_k)
    return ok, time.monotonic() - t0, printable


def wait_for_evaluate(cmd: list[str], done_marker: Path) -> bool:
    """Run evaluate, but treat ITS ARTIFACTS as completion, not its exit code.

    OBSERVED 2026-07-25 on the 148-task ground-truth pass: evaluate computed every result and
    wrote its cache, then never exited — it sat for 20+ minutes with an idle child and no CPU.
    Cause: both `untrusted_check` (eval/__init__.py:184) and `trusted_check`
    (gen/util/__init__.py:108) create a `multiprocessing.Manager()` per task and never shut it
    down, so 148 non-daemonic manager processes are left behind and the pool's shutdown blocks
    joining them. Waiting on the exit code would burn the whole EVAL_TIMEOUT_S per config for
    results that were already correct and already on disk.

    So: poll for `<samples>_pass_at_k.json`, which evaluate writes LAST (evaluate.py:437, after
    eval_results.json). Once it appears, allow a short grace period for a clean exit, then kill
    the process GROUP — which also reaps the leaked managers, since they share the session.
    """
    proc = subprocess.Popen(
        cmd, cwd=str(HERE), stdin=subprocess.DEVNULL, start_new_session=True
    )
    deadline = time.monotonic() + EVAL_TIMEOUT_S
    grace_until = None
    try:
        while time.monotonic() < deadline:
            rc = proc.poll()
            if rc is not None:
                if rc != 0:
                    log(f"  [evaluate] exited rc={rc}")
                return done_marker.exists()
            if done_marker.exists():
                if grace_until is None:
                    grace_until = time.monotonic() + EVAL_EXIT_GRACE_S
                    log(
                        f"  [evaluate] results written; allowing {EVAL_EXIT_GRACE_S}s to exit"
                    )
                elif time.monotonic() > grace_until:
                    log(
                        "  [evaluate] did not exit after writing results (upstream leaks a "
                        "multiprocessing.Manager per task) — killing the process group"
                    )
                    kill_group(proc)
                    return True
            time.sleep(2)
        log(f"  [evaluate] TIMEOUT after {EVAL_TIMEOUT_S}s — killing the process group")
        kill_group(proc)
        return done_marker.exists()
    except KeyboardInterrupt:
        kill_group(proc)
        raise


def kill_group(proc) -> None:
    """SIGTERM then SIGKILL the whole session, so leaked manager processes die with it."""
    for sig in (signal.SIGTERM, signal.SIGKILL):
        try:
            os.killpg(os.getpgid(proc.pid), sig)
        except (ProcessLookupError, PermissionError):
            return
        try:
            proc.wait(timeout=10)
            return
        except subprocess.TimeoutExpired:
            continue


# ---------------------------------------------------------------------------
# artifact -> result JSON
# ---------------------------------------------------------------------------


def read_samples(path: Path) -> list[dict]:
    out = []
    if not path.exists():
        return out
    for line in path.read_text().splitlines():
        line = line.strip()
        if line:
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out


def completion_stats(samples: list[dict]) -> dict:
    """Accounting for "the model returned no usable program", separated from "it was wrong".

    `solution` is the sanitizer's output, `raw_solution` what the model actually returned.

    MEASURED, not assumed: `sanitize()` does NOT blank a response it cannot parse — fed
    prose with no code fence it returns that prose verbatim (verified via smoke_offline.py
    --mode empty, 2026-07-25). So an emptiness test alone detects almost nothing, and a
    truncated or prose-only answer would be silently scored as a wrong answer.

    The reliable tell is that the returned text is not parseable Python:
      * a truncated program (the model hit --max-new-tokens mid-function) -> SyntaxError
      * a prose-only answer (the model never wrote code)                  -> SyntaxError
    Both are generation-side problems. If n_unparseable_solutions is non-trivial, raise
    --max-new-tokens and re-run before believing the pass@1.
    """
    n_empty = n_empty_raw = n_sanitizer_dropped = n_unparseable = 0
    for s in samples:
        sol = (s.get("solution") or "").strip()
        raw = (s.get("raw_solution") or "").strip()
        if not sol:
            n_empty += 1
            if raw:
                n_sanitizer_dropped += 1
        else:
            try:
                ast.parse(sol)
            except (SyntaxError, ValueError):
                n_unparseable += 1
        if not raw:
            n_empty_raw += 1
    return {
        "n_empty_completions": n_empty,
        "n_empty_raw_completions": n_empty_raw,
        "n_sanitizer_dropped": n_sanitizer_dropped,
        "n_unparseable_solutions": n_unparseable,
        "n_no_program": n_empty + n_unparseable,
    }


def summarize(samples_path: Path) -> dict:
    """Pull pass@1 and the load-bearing denominators out of BCB's own artifacts."""
    eval_results_path = Path(str(samples_path).replace(".jsonl", "_eval_results.json"))
    pass_at_k_path = Path(str(samples_path).replace(".jsonl", "_pass_at_k.json"))

    samples = read_samples(samples_path)
    task_ids = sorted({s["task_id"] for s in samples if "task_id" in s})
    out = {"task_ids": task_ids, "n_completed": len(task_ids)}
    out.update(completion_stats(samples))

    pk = json.loads(pass_at_k_path.read_text()) if pass_at_k_path.exists() else {}
    out["pass@1"] = pk.get("pass@1")
    out["gt_pass_rate"] = pk.get("gt_pass_rate")
    failed = [t for t in (pk.get("failed_tasks") or []) if t in set(task_ids)]
    # A task whose GROUND TRUTH fails here cannot be passed by any model in this environment:
    # that is an executor/dependency error, not a model error.
    out["n_env_errors"] = len(failed)
    out["env_error_task_ids"] = failed

    if eval_results_path.exists():
        ev = json.loads(eval_results_path.read_text()).get("eval", {})
        n_pass = n_scored = 0
        statuses: dict[str, int] = {}
        for tid, runs in ev.items():
            if tid not in set(task_ids):
                continue
            for r in runs:
                st = r.get("status")
                statuses[st] = statuses.get(st, 0) + 1
                if tid in failed:
                    continue
                n_scored += 1
                n_pass += int(st == "pass")
        out["status_counts"] = statuses
        # pass@1 with environment-broken tasks removed from the denominator — the honest
        # within-fleet number when the executor itself cannot run some references.
        out["pass@1_gt_ok"] = round(n_pass / n_scored, 4) if n_scored else None
        out["n_scored_gt_ok"] = n_scored
    return out


def _env_health_gt_rate():
    """The executor's own ceiling: no model can beat the ground-truth pass rate measured here."""
    if not ENV_HEALTH.exists():
        return None
    try:
        return (json.loads(ENV_HEALTH.read_text()).get("gt_check") or {}).get(
            "gt_pass_rate"
        )
    except json.JSONDecodeError:
        return None


def completions_provenance(n_proxy: int, n_completed: int) -> str:
    """Did the completions being scored actually come from THIS run, through the proxy?

    Every request BCB makes is one proxy log line, so n_proxy_requests < n_completed means
    some scored completion was read off disk — generated at some earlier time, under whatever
    sampling was in force then. That is not a detail: the proxy is the only place the neutral
    block (temperature 0 / top_p 1 / top_k 0 / min_p 0 / no penalties) is injected, because
    BCB's client hardcodes top_p=0.95 and cannot send the rest at all.
    """
    if n_completed == 0:
        return "no completions on disk"
    if n_proxy == 0:
        return (
            "STALE — 0 requests reached eval_proxy in this run, so every scored completion "
            "was read off disk and did NOT go through neutral-sampling injection. This "
            "pass@1 does not measure what this file's `generation` block claims."
        )
    if n_proxy < n_completed:
        return (
            f"PARTIAL — only {n_proxy} of {n_completed} scored completions were generated in "
            "this run through the proxy; the rest were resumed from disk under sampling "
            "this file cannot vouch for."
        )
    return (
        f"this-run — all {n_completed} scored completions were generated through eval_proxy "
        f"({n_proxy} requests logged, neutral sampling injected on each)"
    )


# eval_proxy.strip_reasoning() is TAG-ANCHORED: THINK_BLOCK, ORPHAN_CLOSE, THINK_UNCLOSED and
# HARMONY_ANALYSIS all key off a literal delimiter. A response that reasons in plain prose with
# no tag at all is NOT detected and NOT stripped — MEASURED on this same model by the IFEval
# lane (eval/external/ifeval/README.md, "Reasoning leak: a second, untagged shape"): 13 of 15
# length-truncated responses were unterminated monologue opening "Thinking Process:" with no
# <think>, and were scored as if they were answers. Claiming a blanket `reasoning_stripped:
# true` would overstate coverage on exactly the shape that is unprotected, so the artifact
# names the shapes it covers and the one it does not.
STRIP_SHAPES_COVERED = [
    "<think>…</think>",
    "orphan </think>",
    "unclosed <think>",
    "harmony <|channel|>analysis",
]
STRIP_SHAPE_NOT_COVERED = (
    "untagged reasoning prose (a response that reasons in plain text with no delimiter at all, "
    "e.g. opening 'Thinking Process:'). eval_proxy's stripper is tag-anchored and passes this "
    "shape through unchanged. NOT fixed here by design: a keyword heuristic would corrupt "
    "legitimate prose in docstrings and comments. See eval/external/ifeval/README.md."
)
# Why BigCodeBench is nonetheless not silently corrupted by that gap, unlike IFEval: BCB runs
# every completion through sanitize() (a markdown code-fence extractor) and this script then
# ast.parse()s the result. Untagged prose therefore lands in one of two OBSERVABLE places
# rather than in the score — it is either discarded as non-code by the fence extractor (no
# scoring impact), or it leaves nothing parseable and is counted in n_unparseable_solutions /
# n_no_program. Those two counters are the structural, heuristic-free exposure check for this
# benchmark; IFEval has no equivalent because it scores free text directly.
STRIP_GAP_DETECTOR = (
    "n_unparseable_solutions + n_no_program (top level) are the heuristic-free exposure check: "
    "untagged reasoning that survived into a scored answer cannot be parsed as Python. Both 0 "
    "means no untagged leak reached scoring in this run."
)


def reasoning_strip_report(requested: bool, proxy_stats: dict) -> dict:
    """What stripping ACTUALLY did, not what it was asked to do — and what it does not cover.

    The old field was a bool that echoed the CLI flag back, so it read `true` even on a run
    where the proxy handled zero responses. `requested` keeps that intent; `verdict` is the
    measurement, and the two are allowed to disagree out loud. `shape_not_covered` is there
    because a field that overstates its coverage is worse than no field.
    """
    n_resp = proxy_stats.get("n_requests", 0)
    n_stripped = proxy_stats.get("n_reasoning_stripped_choices", 0)
    if not requested:
        verdict = "disabled (--no-strip-reasoning): raw model output was scored as-is"
    elif n_resp == 0:
        verdict = (
            "UNSUBSTANTIATED: stripping was enabled but the proxy handled 0 responses in "
            "this run, so nothing was observed to be stripped"
        )
    elif n_stripped == 0:
        verdict = (
            f"enabled but a no-op on the TAGGED shapes: none of the {n_resp} responses "
            "contained a reasoning delimiter. This is NOT evidence that no reasoning leaked — "
            "an untagged monologue produces exactly this count too; see shape_not_covered"
        )
    else:
        verdict = (
            f"enabled and observed on the TAGGED shapes: {n_stripped} of {n_resp} responses "
            "had a tagged reasoning wrapper removed before scoring. Says nothing about the "
            "untagged shape in shape_not_covered, which is not detected"
        )
    return {
        "requested": requested,
        "n_responses_seen_by_proxy": n_resp,
        "n_choices_stripped": n_stripped,
        "n_empty_after_strip": proxy_stats.get("n_empty_after_strip", 0),
        "verdict": verdict,
        "shapes_covered": STRIP_SHAPES_COVERED,
        "shape_not_covered": STRIP_SHAPE_NOT_COVERED,
        "untagged_leak_exposure_check": STRIP_GAP_DETECTOR,
    }


def build_result(
    config: dict,
    s: dict,
    gen_s: float,
    eval_s: float,
    wall_s: float,
    base_url: str,
    proxy_url: str,
    enforced: dict,
    proxy_stats: dict,
    strip_reasoning: bool,
    limit: int | None,
    cmds: dict,
) -> dict:
    return {
        "benchmark": "bigcodebench-hard",
        "split": SPLIT,
        "model": config["model"],
        "quant": config["quant"],
        "opencode_model_id": config["opencode_model_id"],
        "pass@1": s.get("pass@1"),
        "pass@1_gt_ok": s.get("pass@1_gt_ok"),
        "n_tasks": limit or N_HARD_TASKS,
        "n_completed": s.get("n_completed", 0),
        "n_empty_completions": s.get("n_empty_completions", 0),
        "n_empty_raw_completions": s.get("n_empty_raw_completions", 0),
        "n_sanitizer_dropped": s.get("n_sanitizer_dropped", 0),
        "n_unparseable_solutions": s.get("n_unparseable_solutions", 0),
        "n_no_program": s.get("n_no_program", 0),
        "n_env_errors": s.get("n_env_errors", 0),
        "env_error_task_ids": s.get("env_error_task_ids", []),
        "gt_pass_rate": s.get("gt_pass_rate"),
        "status_counts": s.get("status_counts", {}),
        "executor": {
            "mode": "local",
            "pins": "relaxed",
            "rlimits": RLIMIT_NOTE,
            "parallel": EVAL_PARALLEL,
            "env_health": str(ENV_HEALTH),
            "gt_pass_rate_ceiling": _env_health_gt_rate(),
        },
        "generation": {
            "max_new_tokens": MAX_NEW_TOKENS,
            "greedy": True,
            "endpoint": proxy_url,
            "upstream": base_url,
            "sampling_injected": enforced,
            "n_proxy_requests": proxy_stats.get("n_requests", 0),
            "proxy_stats": proxy_stats,
            "completions_provenance": completions_provenance(
                proxy_stats.get("n_requests", 0), s.get("n_completed", 0)
            ),
            "reasoning_stripped": reasoning_strip_report(strip_reasoning, proxy_stats),
            "batch_size": 1,
        },
        "comparability": (
            "within-fleet only; relaxed-pin local executor, NOT comparable to the "
            "public BigCodeBench leaderboard"
        ),
        "commands": cmds,
        "bigcodebench_version": BCB_VERSION,
        "schema_version": SCHEMA_VERSION,
        "wall_clock_s": round(wall_s, 1),
        "generate_s": round(gen_s, 1),
        "evaluate_s": round(eval_s, 1),
        "ts": now_iso(),
    }


# ---------------------------------------------------------------------------
# per-config driver
# ---------------------------------------------------------------------------


def run_config(config: dict, args, upstream_host: str, proxy_url: str) -> dict | None:
    tag = f"{config['model']}__{config['quant']}"
    log(f"\n=== {tag} ({config['opencode_model_id']}) ===")
    root = GEN_DIR / tag
    root.mkdir(parents=True, exist_ok=True)
    proxy_log = root / "eval_proxy.jsonl"
    serve_log = root / "serve.log"
    # eval_proxy appends; a stale log from an earlier run would inflate n_proxy_requests and
    # let a since-changed sampling block be reported as this run's. Stamped rather than a
    # single ".prev", which each run used to overwrite — that is how the evidence for the
    # 2026-07-25 generation got clobbered by the 2026-07-26 rerun that produced nothing.
    stash_stale(proxy_log)
    if not args.dry_run:
        if args.resume:
            log(
                "  [generate] --resume: completions already on disk will be REUSED; "
                "generation.completions_provenance will record how many."
            )
        else:
            n = stash_previous_generations(root)
            if n:
                log(
                    f"  [generate] {n} samples file(s) from an earlier run moved aside; "
                    "every task will be regenerated through the proxy"
                )

    env = dict(os.environ)
    env["OPENAI_API_KEY"] = orchestrate.api_key()  # same fallback key the harness uses

    t_start = time.monotonic()
    proc = proxy = None
    ready = args.dry_run
    try:
        if not args.dry_run:
            if args.no_serve:
                log("  [serve] --no-serve: the endpoint is assumed to be up already")
                ready = True
            else:
                assert_not_llama_swap(orchestrate.PORT)
                proc, ready = orchestrate.serve_config(config, serve_log)
            if not ready:
                log(f"  SKIP {tag}: server never became ready (see {serve_log})")
                return None
            proxy, _ = start_proxy(
                upstream_host, args.proxy_port, proxy_log, args.strip_reasoning
            )

        samples, gen_s, gen_cmd = run_generate(
            config["opencode_model_id"], root, proxy_url, args.limit, env, args.dry_run
        )
        if args.dry_run:
            fake = samples_path_for(root, config["opencode_model_id"])
            run_evaluate(fake, ["<ids from samples>"], bool(args.limit), True)
            log("  [dry-run] nothing executed")
            return None
        if samples is None:
            log(f"  SKIP {tag}: generation produced no samples file")
            return None
    finally:
        stop_proxy(proxy)
        if proc is not None:
            orchestrate.unload(proc)

    # Evaluation is CPU-only and must NOT hold the GPU/RAM: the model is already unloaded.
    stats_pre = summarize(samples)
    ok, eval_s, eval_cmd = run_evaluate(
        samples, stats_pre["task_ids"], bool(args.limit), False
    )
    if not ok:
        log(f"  WARNING {tag}: evaluate failed; writing what artifacts exist")

    s = summarize(samples)
    enforced, n_req = read_proxy_log(proxy_log)
    result = build_result(
        config,
        s,
        gen_s,
        eval_s,
        time.monotonic() - t_start,
        args.base_url,
        proxy_url,
        enforced,
        n_req,
        args.strip_reasoning,
        args.limit,
        {"generate": gen_cmd, "evaluate": eval_cmd},
    )
    out_path = Path(args.out) / f"bcb__{tag}.json"
    atomic_write_json(out_path, result)
    log(
        f"  pass@1={result['pass@1']} (gt-ok {result['pass@1_gt_ok']}) "
        f"n_completed={result['n_completed']} no_program={result['n_no_program']} "
        f"env_errors={result['n_env_errors']} wall={result['wall_clock_s']}s"
    )
    log(f"  -> {out_path}")
    return result


def estimate(configs: list[dict]) -> int:
    """Wall-clock projection from round 1's speed probes — no model, no run.

    148 x 15 is a multi-night commitment; that should be known BEFORE a night is spent, not
    after. Uses each config's measured decode rate and TTFT at the ~1.5K-token probe point,
    which is the right neighbourhood for a BigCodeBench-Hard instruct prompt. Output length is
    the assumption, not the measurement: reasoning models are budgeted at 2000 generated
    tokens, non-reasoning at 600, and the 4096 cap gives the worst case.
    """
    log(
        f"{'config':18} {'reasoning':10} {'decode t/s':>10} {'ttft s':>7} {'est/148':>9}"
    )
    total_min = 0.0
    missing = []
    for c in configs:
        tag = f"{c['model']}__{c['quant']}"
        probe = RESULTS_DIR / f"probe__{tag}.json"
        if not probe.exists():
            missing.append(tag)
            continue
        try:
            point = json.loads(probe.read_text())["points"][0]
            decode = point["decode_tps_median"]
            ttft_s = point["ttft_ms_median"] / 1000
        except (KeyError, IndexError, TypeError, json.JSONDecodeError):
            missing.append(tag)
            continue
        n_out = 2000 if c.get("reasoning") == "on" else 600
        minutes = (ttft_s + n_out / decode) * N_HARD_TASKS / 60
        total_min += minutes
        log(
            f"{tag:18} {c.get('reasoning', '?'):10} {decode:10.1f} {ttft_s:7.2f} "
            f"{minutes:8.0f}m  (assuming {n_out} generated tokens)"
        )
    log(
        f"\n  {len(configs) - len(missing)} config(s): ~{total_min / 60:.1f} h of GENERATION "
        f"for {N_HARD_TASKS} tasks each, 1 rep"
    )
    log(f"  worst case at the {MAX_NEW_TOKENS}-token cap: ~{total_min / 60 * 2:.0f} h")
    log(
        "  excludes model load/unload (~1-2 min per config) and local evaluation "
        "(CPU-bound, minutes per config, and it can run after the model is unloaded)"
    )
    if missing:
        log(f"  no usable speed probe for: {', '.join(missing)}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument(
        "--only", help="restrict to one model name (e.g. opus) or model__quant"
    )
    ap.add_argument(
        "--limit",
        type=int,
        default=None,
        help="dev run: only the first N Hard tasks (generate --id-range 0-N + "
        "evaluate --selective-evaluate)",
    )
    ap.add_argument("--out", default=str(RESULTS_DIR), help="directory for bcb__*.json")
    ap.add_argument(
        "--base-url",
        default="http://127.0.0.1:8888/v1",
        help="UPSTREAM served endpoint the proxy forwards to",
    )
    ap.add_argument("--configs", default=str(HARNESS_DIR / "configs.json"))
    ap.add_argument("--proxy-port", type=int, default=PROXY_PORT)
    ap.add_argument(
        "--strip-reasoning",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="forward --strip-reasoning/--no-strip-reasoning to eval_proxy; ON by "
        "default because served models leak a literal <think> into "
        "message.content with no reasoning_content field (see PROVENANCE.md / "
        "eval_proxy.py). Use --no-strip-reasoning only if the leak probe says "
        "a model needs it off.",
    )
    ap.add_argument(
        "--resume",
        action="store_true",
        help="REUSE completions already on disk instead of regenerating them. Off by "
        "default: BCB's own --resume stays on its command line either way (see "
        "docstring item 3), so without this flag any samples file from an "
        "earlier run is moved aside first and every task is generated afresh "
        "through eval_proxy. Use only to finish a crashed long run.",
    )
    ap.add_argument(
        "--no-serve",
        action="store_true",
        help="do not start/stop a model server; assume --base-url is already "
        "answering (used by smoke_offline.py and for external endpoints)",
    )
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="print the exact commands and exit; serves nothing",
    )
    ap.add_argument(
        "--estimate",
        action="store_true",
        help="project wall clock from round-1 speed probes and exit; runs nothing",
    )
    args = ap.parse_args()

    if not args.estimate:
        preflight(args.dry_run, args.base_url)

    configs = json.loads(Path(args.configs).read_text())
    selected = []
    for c in configs:
        if c.get("broken"):
            continue
        if args.only and args.only not in (c["model"], f"{c['model']}__{c['quant']}"):
            continue
        selected.append(c)
    if not selected:
        raise SystemExit(
            f"ABORT: no configs match --only {args.only!r} in {args.configs}"
        )

    if args.estimate:
        return estimate(selected)

    upstream_host = args.base_url.rsplit("/v1", 1)[0].rstrip("/")
    proxy_url = f"http://127.0.0.1:{args.proxy_port}/v1"

    log(
        f"BigCodeBench-{SUBSET} ({SPLIT}) · {len(selected)} config(s) · "
        f"{args.limit or N_HARD_TASKS} tasks each"
    )
    log(f"  upstream {upstream_host} -> proxy {proxy_url}")
    log("  executor: local, relaxed pins => WITHIN-FLEET comparison only")

    results, t0 = [], time.monotonic()
    for config in selected:
        try:
            r = run_config(config, args, upstream_host, proxy_url)
        except KeyboardInterrupt:
            log("\ninterrupted")
            break
        if r:
            results.append(r)

    total = time.monotonic() - t0
    log(f"\n{len(results)} config(s) in {total / 60:.1f} min")
    if results:
        per_task = [r["wall_clock_s"] / max(r["n_completed"], 1) for r in results]
        avg = sum(per_task) / len(per_task)
        log(
            f"  mean {avg:.1f}s/task -> a full {N_HARD_TASKS}-task config ~= "
            f"{avg * N_HARD_TASKS / 60:.0f} min; 15 configs ~= "
            f"{avg * N_HARD_TASKS * 15 / 3600:.1f} h"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
