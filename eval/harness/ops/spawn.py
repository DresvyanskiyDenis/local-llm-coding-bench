# /// script
# requires-python = ">=3.11"
# ///
"""spawn.py <model> — launch run_model.sh in its OWN session and return immediately.

Why: the first opus attempt died because run_model.sh ran as a *tracked background task*
of the agent's shell; when that task group was SIGTERM'd externally (~23:36, mid-q4), the
kill cascaded into orchestrate and tore the whole run down. start_new_session=True puts the
benchmark in a fresh session/process-group so a kill of the caller's group can never reach
it. The agent then polls DONE__<model>.marker from short-lived (killable, disposable)
heartbeats — disk is the only source of truth. run_model.sh's own 6h wall-clock cap still
bounds the detached run.
"""
import subprocess
import sys
from pathlib import Path

model = sys.argv[1] if len(sys.argv) > 1 else sys.exit("usage: spawn.py <model>")
# this script lives in eval/harness/ops/; run_model.sh is one level up in eval/harness/.
harness = Path(__file__).resolve().parent.parent
log = harness.parent / "results" / "logs" / f"detached__{model}.log"
log.parent.mkdir(parents=True, exist_ok=True)
f = open(log, "a")
p = subprocess.Popen(
    ["bash", str(harness / "run_model.sh"), model],
    stdout=f,
    stderr=subprocess.STDOUT,
    start_new_session=True,
    cwd=str(harness),
)
print(f"detached run_model.sh {model} pid={p.pid} (new session) -> {log}")
