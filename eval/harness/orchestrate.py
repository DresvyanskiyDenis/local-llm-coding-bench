#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "httpx>=0.27",
# ]
# ///
"""Resumable orchestration engine for the local-LLM agentic eval (see ../PLAN.md, CONTRACT.md).

Loops over harness/configs.json; for each config: serve it via ~/bin/unsloth-serve,
wait for it to come up (with zombie/rebind checks), speed-probe it, smoke-test its
tool-calling, then run every (suite, task, rep) unit for the requested stage(s)
through opencode_driver.py + the matching grader(s), sample RAM once per config
(during the largest-context unit), assemble the CONTRACT §4 unit JSON, write it
atomically, append a manifest.jsonl line, and unload the model before moving on.

Idempotent: a unit is done iff results/<unit>.json exists, so --resume is just
re-running this script. A crash loses at most the in-flight unit.

Usage:
    uv run orchestrate.py --dry-run
    uv run orchestrate.py --resume --stage 1
    uv run orchestrate.py --resume --stage 2 --only qwen
"""

import argparse
import json
import os
import re
import signal
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

HARNESS_DIR = Path(__file__).resolve().parent
EVAL_DIR = HARNESS_DIR.parent
BASE_DIR = EVAL_DIR.parent
TASKS_DIR = EVAL_DIR / "tasks"
RESULTS_DIR = EVAL_DIR / "results"
RUNS_DIR = EVAL_DIR / "runs"
CONFIGS_PATH = HARNESS_DIR / "configs.json"
DRIVER_PATH = HARNESS_DIR / "opencode_driver.py"
GRADERS_DIR = HARNESS_DIR / "graders"
PYTEST_GRADER = GRADERS_DIR / "pytest_grader.py"
REVIEW_GRADER = GRADERS_DIR / "review_grader.py"
DIFF_GRADER = GRADERS_DIR / "diff_grader.py"
SMOKE_TEST_PATH = BASE_DIR / "bench" / "smoke_test.py"
SPEED_PROBE_PATH = HARNESS_DIR / "speed_probe.py"
UNSLOTH_SERVE = Path.home() / "bin" / "unsloth-serve"
OPENCODE_CONFIG = Path.home() / ".config" / "opencode" / "opencode.json"

API_BASE = "http://127.0.0.1:8888/v1"
# Same fallback key already committed in speed_probe.py — kept identical so both
# scripts agree without either one needing the real secret from the environment.
DEFAULT_API_KEY_FALLBACK = "sk-local-dummy-key"
PORT = 8888

SUITES = ["A_coding", "B_review", "C_edit", "D_text"]
REQUIRED_CONFIG_KEYS = {
    "model", "quant", "serve_name", "opencode_model_id",
    "real_ctx", "probe_max_ctx", "mtp", "reasoning", "broken",
}
REQUIRED_META_KEYS = {
    "id", "suite", "title", "grader", "timeout_s", "est_ctx_tokens", "entrypoint", "grade",
}

REPS_BY_STAGE = {1: [1], 2: [2, 3]}


def api_key():
    return os.environ.get("UNSLOTH_STUDIO_API_KEY") or DEFAULT_API_KEY_FALLBACK


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def atomic_write_json(path, obj):
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2))
    os.replace(tmp, path)


# ---------------------------------------------------------------------------
# configs.json
# ---------------------------------------------------------------------------

def load_configs():
    return json.loads(CONFIGS_PATH.read_text())


def save_configs(configs):
    atomic_write_json(CONFIGS_PATH, configs)


def mark_broken(configs, config):
    for c in configs:
        if c["serve_name"] == config["serve_name"]:
            c["broken"] = True
    save_configs(configs)
    config["broken"] = True


# ---------------------------------------------------------------------------
# task discovery
# ---------------------------------------------------------------------------

def discover_tasks():
    """Yield (suite, task_id, meta, task_dir) for every tasks/<suite>/<id>/ dir."""
    if not TASKS_DIR.is_dir():
        return
    for suite in SUITES:
        suite_dir = TASKS_DIR / suite
        if not suite_dir.is_dir():
            continue
        for task_dir in sorted(suite_dir.iterdir()):
            meta_path = task_dir / "meta.json"
            if not meta_path.is_file():
                continue
            try:
                meta = json.loads(meta_path.read_text())
            except json.JSONDecodeError:
                continue
            yield suite, task_dir.name, meta, task_dir


# ---------------------------------------------------------------------------
# dry-run validation (no model launch)
# ---------------------------------------------------------------------------

def parse_serve_names(text):
    """Case labels in ~/bin/unsloth-serve, e.g. '  qwen)' -> 'qwen'. Skips the '*)' default."""
    names = set()
    for m in re.finditer(r"(?m)^\s{2}([A-Za-z0-9_.|-]+)\)", text):
        for part in m.group(1).split("|"):
            names.add(part)
    return names


def compiles_clean(path):
    try:
        compile(path.read_text(), str(path), "exec")
        return True, None
    except SyntaxError as e:
        return False, str(e)


def dry_run():
    checks = []  # (name, status, detail)  status in PASS/FAIL/PENDING

    # configs.json
    try:
        configs = load_configs()
        bad = []
        for c in configs:
            missing = REQUIRED_CONFIG_KEYS - c.keys()
            if missing:
                bad.append(f"{c.get('serve_name','?')}: missing {missing}")
        if bad:
            checks.append(("configs.json schema", "FAIL", "; ".join(bad)))
        else:
            checks.append(("configs.json schema", "PASS", f"{len(configs)} configs"))
    except Exception as e:
        configs = []
        checks.append(("configs.json schema", "FAIL", str(e)))

    # serve names
    if configs:
        if UNSLOTH_SERVE.is_file():
            serve_names = parse_serve_names(UNSLOTH_SERVE.read_text())
            missing = [c["serve_name"] for c in configs if c["serve_name"] not in serve_names]
            if missing:
                checks.append(("serve_name in unsloth-serve", "FAIL", f"not found: {missing}"))
            else:
                checks.append(("serve_name in unsloth-serve", "PASS", f"{len(configs)}/{len(configs)} resolved"))
        else:
            checks.append(("serve_name in unsloth-serve", "FAIL", f"{UNSLOTH_SERVE} not found"))

    # opencode model ids
    if configs:
        if OPENCODE_CONFIG.is_file():
            oc = json.loads(OPENCODE_CONFIG.read_text())
            ids = set(oc.get("provider", {}).get("unsloth-studio", {}).get("models", {}).keys())
            missing = sorted({c["opencode_model_id"] for c in configs} - ids)
            if missing:
                checks.append(("opencode_model_id registered", "FAIL", f"not in opencode.json: {missing}"))
            else:
                checks.append(("opencode_model_id registered", "PASS", f"{len(ids)} ids in opencode.json, all referenced ids present"))
        else:
            checks.append(("opencode_model_id registered", "FAIL", f"{OPENCODE_CONFIG} not found"))

    # task dirs
    tasks = list(discover_tasks())
    if not TASKS_DIR.is_dir():
        checks.append(("task dirs (eval/tasks/)", "PENDING", "tasks/ does not exist yet (COMPONENT 1)"))
    elif not tasks:
        checks.append(("task dirs (eval/tasks/)", "PENDING", "tasks/ exists but no task dirs with meta.json found yet"))
    else:
        bad = []
        for suite, task_id, meta, task_dir in tasks:
            missing = REQUIRED_META_KEYS - meta.keys()
            if missing:
                bad.append(f"{suite}/{task_id}: missing {missing}")
        if bad:
            checks.append(("task dirs (eval/tasks/)", "FAIL", "; ".join(bad)))
        else:
            checks.append(("task dirs (eval/tasks/)", "PASS", f"{len(tasks)} tasks parse across {len(SUITES)} suites"))

    # driver + graders (may still be landing — pending, not fail)
    for label, path in [
        ("opencode_driver.py", DRIVER_PATH),
        ("graders/pytest_grader.py", PYTEST_GRADER),
        ("graders/review_grader.py", REVIEW_GRADER),
        ("graders/diff_grader.py", DIFF_GRADER),
    ]:
        if not path.is_file():
            checks.append((label, "PENDING", "not landed yet (COMPONENT 2)"))
            continue
        ok, err = compiles_clean(path)
        checks.append((label, "PASS" if ok else "FAIL", "syntax OK" if ok else err))

    # our own hard dependencies, should already exist
    for label, path in [("bench/smoke_test.py", SMOKE_TEST_PATH), ("harness/speed_probe.py", SPEED_PROBE_PATH)]:
        checks.append((label, "PASS" if path.is_file() else "FAIL", str(path)))

    width = max(len(c[0]) for c in checks)
    print(f"{'check'.ljust(width)}  status   detail")
    print("-" * (width + 60))
    for name, status, detail in checks:
        print(f"{name.ljust(width)}  {status:<7}  {detail}")

    fails = [c for c in checks if c[1] == "FAIL"]
    pendings = [c for c in checks if c[1] == "PENDING"]
    print()
    print(f"{len(checks) - len(fails) - len(pendings)} PASS, {len(pendings)} PENDING, {len(fails)} FAIL")
    return 1 if fails else 0


# ---------------------------------------------------------------------------
# serve lifecycle: launch, ready-wait, zombie/rebind check, unload
# ---------------------------------------------------------------------------

def lsof_listen_pids(port):
    try:
        out = subprocess.run(["lsof", "-nP", f"-iTCP:{port}", "-sTCP:LISTEN", "-t"],
                              capture_output=True, text=True, timeout=10)
        return [p for p in out.stdout.split() if p]
    except Exception:
        return []


def live_llama_server_pids():
    try:
        out = subprocess.run(["pgrep", "-f", "llama-server"], capture_output=True, text=True, timeout=10)
        return [p for p in out.stdout.split() if p]
    except Exception:
        return []


def kill_pid(pid, sig=signal.SIGTERM):
    try:
        os.kill(int(pid), sig)
    except (ProcessLookupError, ValueError):
        pass


def pid_command(pid):
    """Full command line of `pid` ('' if it is gone). Identity by command name, never
    by a remembered pid — pids are recycled and llama-swap restarts on its own."""
    try:
        out = subprocess.run(["ps", "-p", str(pid), "-o", "command="],
                             capture_output=True, text=True, timeout=10)
        return out.stdout.strip()
    except Exception:
        return ""


def llama_swap_listeners(port=PORT):
    """[(pid, command), ...] for listeners on `port` that are llama-swap."""
    out = []
    for pid in lsof_listen_pids(port):
        cmd = pid_command(pid)
        if "llama-swap" in cmd.split("/")[-1] or "/llama-swap" in cmd:
            out.append((pid, cmd))
    return out


def clear_port(port=PORT, wait_s=15):
    """Kill whatever holds `port` — a live server from a prior config, or a zombie
    Studio parent (see setup/UNSLOTH-CHEATSHEET.md). We own the port exclusively
    while this engine runs, so anything there is stale by definition.

    Except since 2026-07-21 that premise is false in daily mode: :8888 belongs to
    llama-swap (LaunchAgent com.user.llama-swap), and killing it silently would take
    OpenCode's whole fleet down and remove exactly the visible conflict it exists to
    raise. Fail loud instead — flipping the machine into eval mode is the operator's
    call, not this function's (IMPLEMENTATION_PLAN.md §3.5 bite 1)."""
    swap = llama_swap_listeners(port)
    if swap:
        raise SystemExit(
            f"REFUSING to clear :{port}: it is held by llama-swap "
            f"(pid {swap[0][0]}: {swap[0][1]}), not by an eval server.\n"
            "Killing it would take OpenCode's daily fleet down. Put the machine in\n"
            "eval mode first, then re-run:\n"
            "    eval/harness/ops/serving_mode.sh eval\n"
            "and restore it afterwards with:\n"
            "    eval/harness/ops/serving_mode.sh daily"
        )
    pids = lsof_listen_pids(port)
    for pid in pids:
        kill_pid(pid, signal.SIGTERM)
    deadline = time.monotonic() + wait_s
    while time.monotonic() < deadline and lsof_listen_pids(port):
        time.sleep(0.5)
    # still there -> force
    for pid in lsof_listen_pids(port):
        kill_pid(pid, signal.SIGKILL)
    for pid in live_llama_server_pids():
        kill_pid(pid, signal.SIGKILL)
    time.sleep(1)


def wait_for_ready(model_id, timeout=300, poll=3):
    """Readiness = a real 1-token completion returns 200, NOT /v1/models returning 200.
    Studio answers GET /v1/models the instant it binds :8888, but loads the weights
    lazily *after* that; a chat request in the gap returns HTTP 400 "No model loaded.
    Call POST /inference/load first." (confirmed 2026-07-12: the first qwen dry-run's
    probe/smoke fired into that window and every request 400'd, wrongly marking both
    quants broken). Studio auto-loads — no explicit POST /inference/load needed
    (verified empirically) — so polling chat/completions until 200 is sufficient; a
    cold model-swap load can take up to ~2 min, which the 300s timeout covers."""
    deadline = time.monotonic() + timeout
    headers = {"Authorization": f"Bearer {api_key()}", "Content-Type": "application/json"}
    body = {
        "model": model_id,
        "messages": [{"role": "user", "content": "ok"}],
        "max_tokens": 1,
        "temperature": 0,
        "stream": False,
    }
    while time.monotonic() < deadline:
        try:
            r = httpx.post(f"{API_BASE}/chat/completions", headers=headers, json=body, timeout=60)
            if r.status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(poll)
    return False


def detect_rebind():
    """Studio silently rebinds to :8889 (then :8890, ...) if :8888 was already busy
    at launch time. If we cleared :8888 first and it's STILL not answering while
    :8889 now has a listener, that's the rebind — treat the config as broken."""
    return bool(lsof_listen_pids(8889))


def serve_config(config, log_path):
    clear_port(PORT)
    log_f = open(log_path, "w")
    proc = subprocess.Popen(
        [str(UNSLOTH_SERVE), config["serve_name"]],
        stdout=log_f, stderr=subprocess.STDOUT, start_new_session=True,
    )
    proc._log_f = log_f  # kept alive + closed in unload(); Popen only dups the fd
    ready = wait_for_ready(config["opencode_model_id"])
    if not ready:
        detail = "rebind to :8889 detected (Studio silent-port-shift)" if detect_rebind() else "no response on :8888 before timeout"
        print(f"  [serve] {config['serve_name']} FAILED to come up: {detail}")
    return proc, ready


def unload(proc):
    if proc is not None:
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
    clear_port(PORT)
    log_f = getattr(proc, "_log_f", None)
    if log_f:
        log_f.close()
    still = live_llama_server_pids()
    if still:
        print(f"  [unload] WARNING: llama-server still alive after unload: {still}")
    else:
        print("  [unload] RAM released, port clear")


# ---------------------------------------------------------------------------
# RAM sampling (once per config, during the largest-context unit — PLAN §5 metric 11)
# ---------------------------------------------------------------------------

def llama_server_rss_kb():
    try:
        out = subprocess.run(["ps", "-eo", "pid,rss,comm"], capture_output=True, text=True, timeout=10)
    except Exception:
        return None
    total = 0
    found = False
    for line in out.stdout.splitlines()[1:]:
        parts = line.split(None, 2)
        if len(parts) < 3:
            continue
        _, rss, comm = parts
        if "llama-server" in comm:
            found = True
            try:
                total += int(rss)
            except ValueError:
                pass
    return total if found else None


def free_kb_vm_stat():
    try:
        out = subprocess.run(["vm_stat"], capture_output=True, text=True, timeout=10)
    except Exception:
        return None
    m = re.search(r"page size of (\d+) bytes", out.stdout)
    page_size = int(m.group(1)) if m else 4096
    m = re.search(r"Pages free:\s+(\d+)", out.stdout)
    if not m:
        return None
    return int(m.group(1)) * page_size / 1024


class RamSampler:
    """Polls RSS/free-mem in the background while a driver subprocess runs."""

    def __init__(self, interval=2):
        self.interval = interval
        self.rss_peak_kb = 0
        self.free_min_kb = None
        self._stop = threading.Event()
        self._thread = None

    def _poll(self):
        while not self._stop.is_set():
            rss = llama_server_rss_kb()
            if rss and rss > self.rss_peak_kb:
                self.rss_peak_kb = rss
            free = free_kb_vm_stat()
            if free is not None and (self.free_min_kb is None or free < self.free_min_kb):
                self.free_min_kb = free
            self._stop.wait(self.interval)

    def __enter__(self):
        self._thread = threading.Thread(target=self._poll, daemon=True)
        self._thread.start()
        return self

    def __exit__(self, *exc):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=5)

    def as_dict(self, sampled_at_ctx_tokens):
        return {
            "rss_peak_gb": round(self.rss_peak_kb / 1024 / 1024, 1) if self.rss_peak_kb else None,
            "free_gb_min": round(self.free_min_kb / 1024 / 1024, 1) if self.free_min_kb is not None else None,
            "sampled_at_ctx_tokens": sampled_at_ctx_tokens,
        }


# ---------------------------------------------------------------------------
# probe + smoke
# ---------------------------------------------------------------------------

def run_speed_probe(config):
    out_path = RESULTS_DIR / f"probe__{config['model']}__{config['quant']}.json"
    if out_path.exists():
        print(f"  [probe] {out_path.name} already exists, skipping")
        return
    cmd = ["uv", "run", str(SPEED_PROBE_PATH),
           "--model", config["opencode_model_id"],
           "--max-ctx", str(config["probe_max_ctx"]),
           "--rounds", "3",
           "--out", str(out_path)]
    print(f"  [probe] {' '.join(cmd)}")
    subprocess.run(cmd, cwd=HARNESS_DIR)


def run_smoke(config):
    out_path = RESULTS_DIR / f"smoke__{config['model']}__{config['quant']}.json"
    cmd = ["uv", "run", str(SMOKE_TEST_PATH),
           "--model", config["opencode_model_id"],
           "--json"]
    print(f"  [smoke] {' '.join(cmd)}")
    proc = subprocess.run(cmd, capture_output=True, text=True, cwd=HARNESS_DIR)
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError:
        print(f"  [smoke] could not parse output, treating as broken: {proc.stdout[:300]!r}")
        return False
    atomic_write_json(out_path, data)
    verdict = data.get("overall_tools_verdict")
    print(f"  [smoke] verdict={verdict}")
    return verdict != "fail"


# ---------------------------------------------------------------------------
# per-unit execution
# ---------------------------------------------------------------------------

def unit_id_for(config, suite, task_id, rep):
    return f"{config['model']}__{config['quant']}__{suite}__{task_id}__rep{rep}"


def result_path(config, suite, task_id, rep):
    return RESULTS_DIR / f"{unit_id_for(config, suite, task_id, rep)}.json"


def run_grader(script, task_dir, run_dir, out_path):
    cmd = ["uv", "run", str(script), "--task", str(task_dir), "--run", str(run_dir), "--out", str(out_path)]
    subprocess.run(cmd, cwd=HARNESS_DIR)
    try:
        return json.loads(out_path.read_text())
    except (FileNotFoundError, json.JSONDecodeError) as e:
        return {"grader": "error", "detail": str(e)}


def grade_unit(meta, task_dir, run_dir):
    grader = meta.get("grader")
    if grader == "pytest":
        return run_grader(PYTEST_GRADER, task_dir, run_dir, run_dir / "grade_pytest.json")
    if grader == "review":
        return run_grader(REVIEW_GRADER, task_dir, run_dir, run_dir / "grade_review.json")
    if grader == "diff_pytest":
        pytest_v = run_grader(PYTEST_GRADER, task_dir, run_dir, run_dir / "grade_pytest.json")
        diff_v = run_grader(DIFF_GRADER, task_dir, run_dir, run_dir / "grade_diff.json")
        return {"pytest": pytest_v, "diff": diff_v}
    if grader == "judge":
        return None  # D_text: driver-only save, Opus judges offline (Stage 3)
    return {"grader": "error", "detail": f"unknown grader {grader!r}"}


def pass_rate_of(grade):
    if grade is None:
        return None
    if "pass_rate" in grade:
        return grade["pass_rate"]
    if "pytest" in grade and isinstance(grade["pytest"], dict):
        return grade["pytest"].get("pass_rate")
    return None


def run_driver(config, task_dir, run_dir, meta, agent, driver_out):
    cmd = ["uv", "run", str(DRIVER_PATH),
           "--task", str(task_dir),
           "--model", config["opencode_model_id"],
           "--agent", agent,
           "--run", str(run_dir),
           "--effort", "high",
           "--timeout", str(meta["timeout_s"]),
           "--out", str(driver_out)]
    log_path = run_dir / "driver.log"
    with open(log_path, "w") as log_f:
        try:
            subprocess.run(cmd, cwd=HARNESS_DIR, stdout=log_f, stderr=subprocess.STDOUT,
                            timeout=meta["timeout_s"] + 60)
        except subprocess.TimeoutExpired:
            print(f"  [driver] hard timeout exceeded for {run_dir.name}, no unit will be written this attempt")
            return None
    if not driver_out.exists():
        print(f"  [driver] no driver.json produced for {run_dir.name} (see {log_path})")
        return None
    try:
        return json.loads(driver_out.read_text())
    except json.JSONDecodeError:
        print(f"  [driver] malformed driver.json for {run_dir.name}")
        return None


def run_unit(config, suite, task_id, meta, task_dir, rep, agent, sample_ram, shared_ram):
    """shared_ram: mutable single-item dict {"value": ...} — filled in on the first
    (largest-context) unit of this config-run and reused as-is for every later unit,
    so all units from one config-run report the same "sampled mid-config" RAM figure
    (PLAN §5 metric #11)."""
    unit_id = unit_id_for(config, suite, task_id, rep)
    out_path = result_path(config, suite, task_id, rep)
    if out_path.exists():
        return  # skip-if-done

    run_dir = RUNS_DIR / unit_id
    if run_dir.exists():
        import shutil
        shutil.rmtree(run_dir)
    run_dir.mkdir(parents=True)

    started_ts = now_iso()
    t0 = time.monotonic()
    driver_out = run_dir / "driver.json"

    if sample_ram:
        sampler = RamSampler()
        with sampler:
            driver_json = run_driver(config, task_dir, run_dir, meta, agent, driver_out)
        shared_ram["value"] = sampler.as_dict(meta.get("est_ctx_tokens"))
    else:
        driver_json = run_driver(config, task_dir, run_dir, meta, agent, driver_out)
    ram = shared_ram["value"]

    if driver_json is None:
        return  # in-flight failure; no result written, --resume retries it

    grade = grade_unit(meta, task_dir, run_dir)
    duration_s = round(time.monotonic() - t0, 1)

    unit = {
        "unit_id": unit_id,
        "model": config["model"], "quant": config["quant"],
        "opencode_model_id": config["opencode_model_id"],
        "suite": suite, "task": task_id, "rep": rep,
        "effort": "high",
        "driver": driver_json,
        "grade": grade,
        "ram": ram,
        "served": {"serve_name": config["serve_name"], "real_ctx": config["real_ctx"], "port": PORT},
        "started_ts": started_ts, "duration_s": duration_s,
        "schema_version": 1,
    }
    atomic_write_json(out_path, unit)

    manifest_line = {
        "unit_id": unit_id,
        "status": driver_json.get("status"),
        "pass_rate": pass_rate_of(grade),
        "ts": now_iso(),
    }
    with open(RESULTS_DIR / "manifest.jsonl", "a") as f:
        f.write(json.dumps(manifest_line) + "\n")
    print(f"  [unit] {unit_id} -> status={manifest_line['status']} pass_rate={manifest_line['pass_rate']}")


# ---------------------------------------------------------------------------
# per-config orchestration
# ---------------------------------------------------------------------------

def task_applies_to_config(meta, config):
    """Optional per-task `configs` in meta.json restricts which configs run that task
    (IMPLEMENTATION_PLAN.md §7 Phase 3 / §8: e.g. D5_longctx_100k at one quant per
    model instead of all 15). Entries match either a config's `model` ("opus" → both
    quants) or its `serve_name` ("opus4" → the q4 lane only). Key absent = all configs,
    which is every meta.json that exists today."""
    allowed = meta.get("configs")
    if not allowed:
        return True
    return config["model"] in allowed or config["serve_name"] in allowed


def planned_units(config, stages):
    tasks = list(discover_tasks())
    default_reps = sorted({r for s in stages for r in REPS_BY_STAGE[s]})
    units = []
    for suite, task_id, meta, task_dir in tasks:
        if not task_applies_to_config(meta, config):
            continue
        # Optional per-task `reps` overrides the stage schedule outright (a slow
        # 100K-context task is worth 1 rep, not 3). Absent = the stage default,
        # i.e. identical planning to every round-1 task.
        reps = meta.get("reps") or default_reps
        for rep in reps:
            units.append((suite, task_id, meta, task_dir, rep))
    return units


def process_config(config, stages, agent, log_dir):
    label = f"{config['model']}/{config['quant']}"
    if config.get("broken"):
        print(f"[config] {label} marked broken in configs.json, skipping entirely")
        return

    units = planned_units(config, stages)
    pending = [u for u in units if not result_path(config, u[0], u[1], u[4]).exists()]
    probe_path = RESULTS_DIR / f"probe__{config['model']}__{config['quant']}.json"
    if not pending and probe_path.exists():
        print(f"[config] {label} fully done for stage(s) {stages}, skipping")
        return

    print(f"[config] {label}: {len(pending)}/{len(units)} units pending")
    log_path = log_dir / f"serve__{config['serve_name']}.log"
    proc, ready = serve_config(config, log_path)
    if not ready:
        mark_broken(load_configs(), config)
        unload(proc)
        return

    try:
        run_speed_probe(config)
        if not run_smoke(config):
            print(f"[config] {label} smoke test failed (0 tools / garbage) -> marking broken, skipping task depth")
            mark_broken(load_configs(), config)
            return
        if not pending:
            return
        # Sample RAM once per config-run, during the largest-context pending unit
        # (PLAN §5 metric #11: "sampled mid-config" under a realistic context),
        # then reuse that same reading for every other unit in this config-run.
        pending_sorted = sorted(pending, key=lambda u: u[2].get("est_ctx_tokens", 0), reverse=True)
        shared_ram = {"value": None}
        for i, (suite, task_id, meta, task_dir, rep) in enumerate(pending_sorted):
            run_unit(config, suite, task_id, meta, task_dir, rep, agent, i == 0, shared_ram)
    finally:
        unload(proc)


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--resume", action="store_true", help="required (with --dry-run) to actually launch models")
    ap.add_argument("--stage", type=int, choices=[1, 2], default=None,
                     help="restrict to one stage; omit to run stage 1 then stage 2")
    ap.add_argument("--only", default=None, help="restrict to configs whose 'model' field matches")
    ap.add_argument("--agent", default="build", help="opencode --agent name passed to the driver")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    RUNS_DIR.mkdir(parents=True, exist_ok=True)

    if args.dry_run:
        sys.exit(dry_run())

    if not args.resume:
        print("refusing to launch models without --resume (use --dry-run to validate only)", file=sys.stderr)
        sys.exit(1)

    stages = [args.stage] if args.stage else [1, 2]
    configs = load_configs()
    if args.only:
        configs = [c for c in configs if c["model"] == args.only]
        if not configs:
            print(f"--only {args.only!r} matched no config", file=sys.stderr)
            sys.exit(1)

    log_dir = RESULTS_DIR / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    for config in configs:
        process_config(config, stages, args.agent, log_dir)


if __name__ == "__main__":
    main()
