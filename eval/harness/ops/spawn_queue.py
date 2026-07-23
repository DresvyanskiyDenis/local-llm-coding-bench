# /// script
# requires-python = ">=3.11"
# ///
"""spawn_queue.py — launch run_queue_night3.sh in its OWN session and return immediately.

Same rationale as spawn.py: a tracked background task of the agent's shell gets reaped, so
the serial night-3 re-run (katdev -> qwopus -> ornith) must live in a fresh session/
process-group. The agent then polls DONE__QUEUE.marker + per-model DONE__<model>.marker from
disposable heartbeats. The queue restores Denis's daily opencode.json via its own exit trap.
"""
import subprocess
from pathlib import Path

# this script and run_queue_night3.sh live in eval/harness/ops/; results live under eval/.
harness = Path(__file__).resolve().parent
log = harness.parent.parent / "results" / "logs" / "detached__queue_night3.log"
log.parent.mkdir(parents=True, exist_ok=True)
f = open(log, "a")
p = subprocess.Popen(
    ["bash", str(harness / "run_queue_night3.sh")],
    stdout=f,
    stderr=subprocess.STDOUT,
    start_new_session=True,
    cwd=str(harness),
)
print(f"detached run_queue_night3.sh pid={p.pid} (new session) -> {log}")
