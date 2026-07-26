# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""How much of BigCodeBench-Hard can this machine actually execute?

MUST be run with the BigCodeBench venv's interpreter, because the whole point is to
introspect *that* environment:

    eval/external/bigcodebench/.venv/bin/python eval/external/bigcodebench/env_health.py

(The PEP 723 header declares no dependencies for exactly that reason: the script imports
nothing outside the stdlib except `bigcodebench` itself, which lives in the venv.)

WHY THIS EXISTS
    Round 2 installs BigCodeBench's `requirements-eval.txt` with the pins STRIPPED, because
    numpy==1.21.2 / numba==0.55.0 / keras==2.11.0 / gensim==4.3.2 / tensorflow==2.11.0 have no
    Apple-Silicon wheels (IMPLEMENTATION_PLAN.md §1, "the one genuine unknown"). A task whose
    test imports a module that is missing here fails for an ENVIRONMENT reason, not because the
    model was wrong. This script counts that up front, so the number is known before anything
    depends on it, and so `n_env_errors` in the result JSON has a baseline to be compared against.

    Every config runs under this identical executor, so the WITHIN-FLEET ranking is unaffected.
    The absolute pass@1 is NOT comparable to the public BigCodeBench leaderboard.

WHAT IT MEASURES
    For each of the 148 Hard tasks, the set of top-level modules its `test` source imports
    (statically, via `ast`, which also catches imports nested inside test methods). A task is
    "resolvable" when every one of those modules can be located by `importlib.util.find_spec`.
    Reported alongside: the same count when the task's own solution imports are included, which
    is the stricter and more realistic bound, since `untrusted_check` executes solution + test
    in one process.

    --gt-check adds the STRONGER number, and it needs no model: it runs BigCodeBench's own
    `evaluate --check-gt-only --execution local`, which executes all 148 CANONICAL solutions
    against their tests in this very environment. Import-resolvability is necessary but not
    sufficient — a task can import numpy fine and still fail on a relaxed-pin API change. Any
    task the ground truth cannot pass here is an environment error by construction, and is the
    ceiling on every model's pass@1. Slow (minutes); worth it once.

Writes env_health.json next to this file.
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import platform
import re
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone
from importlib import metadata
from importlib.util import find_spec
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "env_health.json"
REQ_EVAL = HERE / "requirements-eval-0.2.5.txt"
WORK = HERE / "_work"


def top_level_imports(source: str) -> set[str]:
    """Top-level module names imported anywhere in `source` (including inside functions)."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return set()
    mods: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                mods.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            # `from . import x` has no module; relative imports never leave the test file.
            if node.module and node.level == 0:
                mods.add(node.module.split(".")[0])
    return mods


def resolvable(mod: str) -> bool:
    if mod in sys.stdlib_module_names or mod in sys.builtin_module_names:
        return True
    try:
        return find_spec(mod) is not None
    except (ImportError, ValueError, AttributeError, TypeError):
        # find_spec imports parent packages; a parent that blows up counts as unresolvable.
        return False
    except Exception:
        return False


def parse_pins(path: Path) -> dict[str, str]:
    pins: dict[str, str] = {}
    if not path.exists():
        return pins
    for line in path.read_text().splitlines():
        line = line.split("#")[0].strip()
        m = re.match(r"^([A-Za-z0-9_.\-]+)\s*==\s*(.+)$", line)
        if m:
            pins[m.group(1).lower().replace("_", "-")] = m.group(2).strip()
    return pins


# MEASURED 2026-07-25 on this machine (Darwin arm64, CPython 3.12.13): every
# resource.setrlimit(RLIMIT_AS | RLIMIT_DATA, v) raises ValueError "current limit exceeds
# maximum limit" for EVERY v tried, from 64 MB to 30 GB, inside and outside the agent sandbox.
# reliability_guard (eval/utils.py:301) applies both unconditionally, so with BigCodeBench's
# defaults the guard raises before the test body ever runs and EVERY task becomes an
# environment failure — a first gt run scored 80 failures in ~90 tasks and would have made
# pass@1 identically 0 for every model in the fleet, indistinguishable from "the model is bad".
#
# The guard's own condition is `if max_as_limit and max_data_limit and max_stack_limit:`, so
# passing 0 skips the whole rlimit block and leaves every other protection (TZ pinning,
# faulthandler off, builtins.exit removed, matplotlib teardown) intact. No vendored code is
# modified. Cost: executed solutions have no memory ceiling, so keep --parallel low.
RLIMIT_FLAGS = [
    "--max-as-limit",
    "0",
    "--max-data-limit",
    "0",
    "--max-stack-limit",
    "0",
]
RLIMIT_NOTE = (
    "rlimits disabled: macOS setrlimit(RLIMIT_AS/RLIMIT_DATA) returns EINVAL at "
    "any value, so BigCodeBench's default 30 GB caps make every task fail in "
    "reliability_guard before the test runs"
)

GT_RATE_RE = re.compile(r"Groundtruth pass rate:\s*([0-9.]+)")
GT_FAILED_RE = re.compile(r"Failed tasks:\s*(\[[^\]]*\])")


def parse_gt_output(text: str) -> dict:
    rate = GT_RATE_RE.search(text)
    failed_raw = GT_FAILED_RE.search(text)
    failed: list[str] = []
    if failed_raw:
        try:
            failed = list(ast.literal_eval(failed_raw.group(1)))
        except (ValueError, SyntaxError):
            failed = []
    return {
        "gt_pass_rate": float(rate.group(1)) if rate else None,
        "failed_tasks": failed,
        "n_failed_tasks": len(failed),
    }


def gt_from_cache() -> dict | None:
    """Read the ground-truth verdict out of BigCodeBench's own timing cache.

    get_groundtruth() pickles {task_id: expected_seconds} and stores None for any task whose
    canonical solution did NOT pass here (evaluate.py:76-83) — i.e. the cache already IS the
    ground-truth result, and it is written before the run's (leaky, hang-prone) shutdown.
    Reading it avoids recomputing 148 executions just to recover a number already on disk.
    Only used when explicitly asked for, so it can never silently substitute a stale run.
    """
    import pickle
    from bigcodebench.data import get_bigcodebench_hash
    from bigcodebench.data.utils import CACHE_DIR

    path = Path(CACHE_DIR) / f"{get_bigcodebench_hash(subset='hard')}.pkl"
    if not path.exists():
        return None
    try:
        cache = pickle.loads(path.read_bytes())
    except Exception as exc:
        print(f"  gt cache unreadable ({type(exc).__name__}); ignoring")
        return None
    failed = sorted(k for k, v in cache.items() if v is None)
    return {
        "gt_pass_rate": round((len(cache) - len(failed)) / len(cache), 4)
        if cache
        else None,
        "failed_tasks": failed,
        "n_failed_tasks": len(failed),
        "n_tasks_in_cache": len(cache),
        "source": f"bigcodebench ground-truth timing cache {path}",
        "rlimits": "disabled",
        "rlimits_reason": RLIMIT_NOTE,
        "note": (
            "gt_pass_rate is the CEILING on every model's pass@1 under this executor; "
            "failed_tasks are environment errors by construction, not model errors."
        ),
    }


GT_EXIT_GRACE_S = 120


def wait_for_gt(proc, log_path: Path) -> bool:
    """Wait for the gt check, treating its OUTPUT as completion rather than its exit.

    OBSERVED 2026-07-25: the 148-task run computed every result and wrote its ground-truth
    cache, then sat for 20+ minutes with an idle child and no CPU. `trusted_check`
    (gen/util/__init__.py:108) creates a `multiprocessing.Manager()` per task and never shuts
    it down, so the pool's shutdown blocks joining 148 leaked non-daemonic processes. The
    numbers were already correct and already printed. Returns True if it had to be killed.
    """
    grace_until = None
    while True:
        if proc.poll() is not None:
            return False
        try:
            done = "Groundtruth pass rate" in log_path.read_text(errors="replace")
        except OSError:
            done = False
        if done:
            if grace_until is None:
                grace_until = time.monotonic() + GT_EXIT_GRACE_S
                print(
                    f"  results printed; allowing {GT_EXIT_GRACE_S}s for a clean exit"
                )
            elif time.monotonic() > grace_until:
                print(
                    "  did not exit (upstream leaks a Manager per task) — killing the group"
                )
                for sig in (signal.SIGTERM, signal.SIGKILL):
                    try:
                        os.killpg(os.getpgid(proc.pid), sig)
                        proc.wait(timeout=10)
                        break
                    except (ProcessLookupError, PermissionError):
                        break
                    except subprocess.TimeoutExpired:
                        continue
                return True
        time.sleep(5)


def run_gt_check(parallel: int, log_path: Path) -> dict:
    """Execute all 148 canonical solutions locally via BigCodeBench's own gt checker.

    `--samples __dummy__.jsonl` is required even though nothing is read from it: evaluate()
    asserts samples is not None before the check_gt_only branch replaces it with that exact
    dummy name (evaluate.py:145,235). The file need not exist.
    """
    WORK.mkdir(parents=True, exist_ok=True)
    cmd = [
        sys.executable,
        "-m",
        "bigcodebench.evaluate",
        "--split",
        "instruct",
        "--subset",
        "hard",
        "--execution",
        "local",
        "--samples",
        "__dummy__.jsonl",
        "--check-gt-only",
        "--parallel",
        str(parallel),
        *RLIMIT_FLAGS,
    ]
    print(f"  running ground-truth check: {' '.join(cmd)}")
    print(f"  live log: {log_path}")
    t0 = time.monotonic()
    # Streamed to a file, not captured: this takes tens of minutes and silence is
    # indistinguishable from a hang.
    with open(log_path, "w") as log_f:
        proc = subprocess.Popen(
            cmd,
            cwd=str(WORK),
            stdout=log_f,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
        )
        killed = wait_for_gt(proc, log_path)
    dt = time.monotonic() - t0
    text = log_path.read_text(errors="replace")
    out = parse_gt_output(text)
    out.update(
        {
            "parallel": parallel,
            "wall_clock_s": round(dt, 1),
            "returncode": proc.returncode,
            "killed_after_completion": killed,
            "log": str(log_path),
            "rlimits": "disabled",
            "rlimits_reason": RLIMIT_NOTE,
            "n_setrlimit_errors": (proc.stdout + proc.stderr).count(
                "current limit exceeds maximum limit"
            ),
            "note": (
                "gt_pass_rate is the CEILING on every model's pass@1 under this executor; "
                "failed_tasks are environment errors by construction, not model errors."
            ),
        }
    )
    return out


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument(
        "--gt-check",
        action="store_true",
        help="also execute all 148 canonical solutions locally (slow, no model "
        "needed) and record the ground-truth pass rate",
    )
    ap.add_argument(
        "--parallel",
        type=int,
        default=4,
        help="worker processes for --gt-check (default 4; BCB's own default is "
        "cpu_count()//2, which starves everything else on this machine)",
    )
    ap.add_argument(
        "--gt-from-cache",
        action="store_true",
        help="take the ground-truth verdict from BigCodeBench's existing timing "
        "cache instead of re-executing all 148 canonical solutions",
    )
    ap.add_argument("--gt-log", default=str(WORK / "gt_check.out"))
    args = ap.parse_args()

    try:
        from bigcodebench.data import get_bigcodebench
    except ImportError as exc:  # pragma: no cover - operator error
        print(
            f"FATAL: bigcodebench not importable from {sys.executable}: {exc}",
            file=sys.stderr,
        )
        print("Run bootstrap.sh first, and use the venv's python.", file=sys.stderr)
        return 1

    print(
        "Loading BigCodeBench-Hard (downloads the dataset on first run; data, not a model)..."
    )
    problems = get_bigcodebench(subset="hard")
    print(f"  {len(problems)} tasks")

    # module -> set of task ids that need it, split by where the import lives
    need_test: dict[str, set[str]] = {}
    need_solution: dict[str, set[str]] = {}

    task_test_mods: dict[str, set[str]] = {}
    task_all_mods: dict[str, set[str]] = {}

    for task_id, task in problems.items():
        test_mods = top_level_imports(task.get("test", "") or "")
        sol_src = "\n".join(
            str(task.get(k, "") or "")
            for k in ("complete_prompt", "code_prompt", "canonical_solution")
        )
        sol_mods = top_level_imports(sol_src)

        task_test_mods[task_id] = test_mods
        task_all_mods[task_id] = test_mods | sol_mods
        for m in test_mods:
            need_test.setdefault(m, set()).add(task_id)
        for m in sol_mods - test_mods:
            need_solution.setdefault(m, set()).add(task_id)

    all_mods = sorted(set(need_test) | set(need_solution))
    status = {m: resolvable(m) for m in all_mods}
    missing = sorted(m for m, ok in status.items() if not ok)

    def task_ok(mods: set[str]) -> bool:
        return all(status.get(m, False) for m in mods)

    resolvable_test_only = [t for t, mods in task_test_mods.items() if task_ok(mods)]
    resolvable_incl_solution = [t for t, mods in task_all_mods.items() if task_ok(mods)]
    blocked = sorted(set(problems) - set(resolvable_incl_solution))

    # --- version shifts, restricted to distributions the Hard split actually touches -------
    pins = parse_pins(REQ_EVAL)
    try:
        mod_to_dists = metadata.packages_distributions()
    except Exception:
        mod_to_dists = {}

    version_shifts: dict[str, dict[str, str]] = {}
    for mod in all_mods:
        if not status.get(mod):
            continue
        for dist in mod_to_dists.get(mod, []):
            key = dist.lower().replace("_", "-")
            if key not in pins:
                continue
            try:
                installed = metadata.version(dist)
            except metadata.PackageNotFoundError:
                continue
            if installed != pins[key]:
                version_shifts[key] = {"pinned": pins[key], "installed": installed}

    missing_modules = {
        m: {
            "n_tasks": len(need_test.get(m, set()) | need_solution.get(m, set())),
            "in_tests": sorted(need_test.get(m, set()))[:20],
            "in_solutions_only": sorted(need_solution.get(m, set()))[:20],
        }
        for m in missing
    }

    obj = {
        "n_hard_tasks": len(problems),
        "n_resolvable": len(resolvable_test_only),
        "n_resolvable_incl_solution_imports": len(resolvable_incl_solution),
        "n_blocked": len(blocked),
        "blocked_task_ids": blocked,
        "n_distinct_modules": len(all_mods),
        "missing_modules": missing_modules,
        "version_shifts": version_shifts,
        "notes": (
            "n_resolvable counts tasks whose TEST imports all resolve. "
            "n_resolvable_incl_solution_imports additionally requires the task's own "
            "solution imports to resolve, which is the bound that matters because "
            "untrusted_check executes solution + test together. Relaxed pins => "
            "within-fleet comparison only, NOT comparable to the public leaderboard."
        ),
        "requirements_eval": REQ_EVAL.name,
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "python": sys.version.split()[0],
        "executable": sys.executable,
        "platform": f"{platform.system()}-{platform.release()}-{platform.machine()}",
    }

    # A gt_check costs minutes; never silently drop a previous one just because this run
    # was the cheap import-only pass.
    if args.gt_check:
        obj["gt_check"] = run_gt_check(args.parallel, Path(args.gt_log))
    elif args.gt_from_cache:
        cached = gt_from_cache()
        if cached:
            obj["gt_check"] = cached
        else:
            print("  no usable ground-truth cache; run with --gt-check")
    elif OUT.exists():
        try:
            prev = json.loads(OUT.read_text()).get("gt_check")
        except json.JSONDecodeError:
            prev = None
        if prev:
            prev["carried_over_from_earlier_run"] = True
            obj["gt_check"] = prev

    OUT.write_text(json.dumps(obj, indent=2) + "\n")

    print()
    print(
        f"  test imports resolve:            {obj['n_resolvable']}/{obj['n_hard_tasks']}"
    )
    print(
        f"  test+solution imports resolve:   {obj['n_resolvable_incl_solution_imports']}"
        f"/{obj['n_hard_tasks']}"
    )
    print(f"  missing modules ({len(missing)}): {', '.join(missing) or '-'}")
    print(f"  version shifts vs pins: {len(version_shifts)}")
    gt = obj.get("gt_check")
    if gt:
        print(
            f"  ground-truth pass rate:          {gt['gt_pass_rate']} "
            f"({gt['n_failed_tasks']} env-broken tasks)"
        )
    print(f"  -> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
