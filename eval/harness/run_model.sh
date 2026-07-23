#!/bin/bash
# run_model.sh <model> — the ONE serial unit of work per model. The main loop launches this
# as its OWN background Bash command; when it exits, the main loop is reliably re-invoked
# (main-owned bg completion is the supported wake path — we no longer depend on waking an
# idle subagent, which is exactly what hung the qwen run).
#
# It: (1) runs orchestrate under `caffeinate` so display/idle/system sleep + App-Nap can't
# freeze the run or its watchdog under a locked screen (the root cause of the qwen freeze);
# (2) runs the janitor watchdog.sh alongside; (3) blocks until orchestrate exits; (4) stops
# the watchdog, reaps any leaked opencode, verifies :8888 is free; (5) writes a plain-text
# DONE marker so completion can be reconciled from disk even if the wake event is ever lost.
set -u
MODEL="${1:?usage: run_model.sh <model>}"
REPO_ROOT="${REPO_ROOT:-$(cd "$(dirname "$0")/../.." && pwd)}"
HARNESS="$REPO_ROOT/eval/harness"
BASE="$REPO_ROOT/eval"
RESULTS="$BASE/results"
mkdir -p "$RESULTS/logs"
ORCH_LOG="$RESULTS/logs/orch__${MODEL}.log"
MARKER="$RESULTS/DONE__${MODEL}.marker"
rm -f "$MARKER"
cd "$HARNESS" || exit 3

echo "=== $(date '+%F %T') run_model start model=$MODEL ===" >> "$ORCH_LOG"

# orchestrate in background UNDER caffeinate (system stays awake for the whole run — global
# sleep-prevention also covers the sibling watchdog). caffeinate exits when orchestrate does.
caffeinate -ims env PYTHONUNBUFFERED=1 uv run orchestrate.py --resume --only "$MODEL" >> "$ORCH_LOG" 2>&1 &
ORCH=$!

# let orchestrate spawn its python child before the watchdog looks for it
sleep 6
bash "$HARNESS/ops/watchdog.sh" "$MODEL" &
WD=$!

# block until the model's full run finishes — but NEVER forever. A hard wall-clock cap
# guarantees this bg command always exits, so the main loop is always eventually
# re-invoked. The qwen freeze taught us the one rule: never depend on an unbounded wait.
# The watchdog only kills leaked opencode; an orchestrate stuck elsewhere (e.g. waiting on
# serve-readiness) would otherwise pin `wait` until morning. This cap is the backstop.
MAX_SECS=${MAX_SECS:-21600}          # 6h — generous; one model never legitimately exceeds it
DEADLINE=$(( $(date +%s) + MAX_SECS ))
TIMED_OUT=0
while kill -0 "$ORCH" 2>/dev/null; do
  if [ "$(date +%s)" -ge "$DEADLINE" ]; then
    TIMED_OUT=1
    echo "=== $(date '+%F %T') run_model WALL-CLOCK CAP ${MAX_SECS}s hit; aborting orchestrate model=$MODEL ===" >> "$ORCH_LOG"
    kill -TERM "$ORCH" 2>/dev/null; sleep 5; kill -KILL "$ORCH" 2>/dev/null
    break
  fi
  sleep 30
done
wait "$ORCH" 2>/dev/null; RC=$?

# stop the janitor and reap any leaked opencode/node so the NEXT model starts on clean RAM
kill "$WD" 2>/dev/null
pkill -TERM -f "watchdog.sh ${MODEL}" 2>/dev/null
for p in $(pgrep -f "opencode run" 2>/dev/null); do
  pgid=$(ps -o pgid= -p "$p" 2>/dev/null | tr -d ' '); [ -n "$pgid" ] && kill -KILL -"$pgid" 2>/dev/null
done
sleep 2

PORT=$(lsof -nP -iTCP:8888 -sTCP:LISTEN 2>/dev/null | wc -l | tr -d ' ')
UNITS=$(ls -1 "$RESULTS"/${MODEL}__*.json 2>/dev/null | wc -l | tr -d ' ')
UNLOADS=$(grep -c "RAM released, port clear" "$ORCH_LOG" 2>/dev/null)
BROKEN=$(grep -c "marked broken" "$ORCH_LOG" 2>/dev/null)
{
  echo "model=$MODEL"
  echo "orchestrate_rc=$RC"
  echo "timed_out=$TIMED_OUT"
  echo "result_units=$UNITS"
  echo "port_8888_listeners=$PORT"
  echo "unload_lines=$UNLOADS"
  echo "broken_marks=$BROKEN"
  echo "finished_at_epoch=$(date +%s)"
  echo "finished_at=$(date '+%F %T')"
} > "$MARKER"

echo "=== $(date '+%F %T') run_model DONE model=$MODEL rc=$RC units=$UNITS port_listeners=$PORT ===" >> "$ORCH_LOG"
echo "run_model.sh done: model=$MODEL rc=$RC units=$UNITS port_listeners=$PORT broken=$BROKEN"
tail -3 "$ORCH_LOG"
