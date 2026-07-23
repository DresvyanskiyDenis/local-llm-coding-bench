#!/bin/bash
# run_queue.sh — self-driving remainder of the serial benchmark, fully DETACHED.
#
# Why this exists: the agent's *tracked* background tasks are reaped by the harness within
# minutes (observed 2026-07-14 — even a caffeinate-wrapped poller died), so orchestration
# must NOT depend on the agent being woken between models. Only a detached, own-session
# process survives (proved by the opus + glm runs launched via spawn.py). This script chains
# every remaining model end-to-end, strictly serial (one model in RAM), and the agent merely
# observes the on-disk markers/digests and does the final cross-model analysis.
#
# Flow: hold the machine awake for our whole life -> wait for the in-flight glm to finish and
# digest it -> then for each remaining model: run_model.sh (serve->bench->unload, has its own
# 6h cap + janitor watchdog + caffeinate) then the deterministic digest.py. A failing/2timed-out
# model that fails or times out is logged and SKIPPED — the queue never aborts as a whole.
set -u
REPO_ROOT="${REPO_ROOT:-$(cd "$(dirname "$0")/../../.." && pwd)}"
HARNESS="$REPO_ROOT/eval/harness"
BASE="$REPO_ROOT/eval"
RESULTS="$BASE/results"
mkdir -p "$RESULTS/logs"
QLOG="$RESULTS/logs/queue.log"
say(){ echo "$(date '+%F %T') $*" >> "$QLOG"; }

# keep display/idle/system sleep off for the ENTIRE queue (covers the gaps between models
# and the digests, where run_model.sh's own caffeinate isn't holding). -w $$ = assert until
# this script exits.
caffeinate -ims -w $$ &

digest(){ ( cd "$HARNESS" && uv run digest.py "$1" >> "$QLOG" 2>&1 ) && say "digest $1 OK" || say "digest $1 FAILED"; }

say "==== run_queue start (pid $$) ===="

# 1) the in-flight glm run was launched separately (spawn.py glm); wait it out, then digest.
say "waiting for DONE__glm.marker (glm already running detached)"
while [ ! -f "$RESULTS/DONE__glm.marker" ]; do sleep 30; done
say "glm finished -> digest"
digest glm

# 2) remaining models, strictly serial.
for M in gemma gpt-oss northmini qwen27 katdev qwopus ornith; do
  say "==== model $M : run_model start ===="
  bash "$HARNESS/run_model.sh" "$M" >> "$QLOG" 2>&1
  rc=$?
  say "==== model $M : run_model exited rc=$rc -> digest ===="
  digest "$M"
done

say "==== run_queue COMPLETE ===="
touch "$RESULTS/DONE__QUEUE.marker"
