#!/bin/bash
# run_queue_night3.sh — self-driving, DETACHED re-run of ONLY the night-3 models
# (katdev q4+iq4, qwopus q5, ornith q4) after the root cause (opencode-log-sanitizer
# redacting the task) was fixed and the corrupted artifacts were moved aside.
#
# Strictly serial: orchestrate.py --resume --only <model> serves each config itself
# (serve_config -> probe(skip-if-exists) -> smoke -> units -> unload), so this queue just
# chains the three models via run_model.sh (which adds the caffeinate + wall-clock cap +
# janitor watchdog) and runs digest.py after each.
#
# Config scoping: the DAILY ~/.config/opencode/opencode.json is already trimmed to the
# night-3 base-prompt conditions (all MCP stripped, dcp kept) by eval_config_scope.py in
# the foreground before launch. This script RESTORES it verbatim on ANY exit via a trap,
# so the eval-scoping is reversible and never persists past the run.
set -u
REPO_ROOT="${REPO_ROOT:-$(cd "$(dirname "$0")/../../.." && pwd)}"
HARNESS="$REPO_ROOT/eval/harness"
BASE="$REPO_ROOT/eval"
RESULTS="$BASE/results"
mkdir -p "$RESULTS/logs"
QLOG="$RESULTS/logs/queue_night3.log"
say(){ echo "$(date '+%F %T') $*" >> "$QLOG"; }

# restore Denis's daily config on ANY exit (normal, error, or TERM/INT).
restore_config(){ ( cd "$HARNESS" && uv run eval_config_scope.py restore >> "$QLOG" 2>&1 ) || true; }
trap restore_config EXIT INT TERM

# keep the machine awake for the whole queue (covers gaps between models + digests).
caffeinate -ims -w $$ &

digest(){ ( cd "$HARNESS" && uv run digest.py "$1" >> "$QLOG" 2>&1 ) && say "digest $1 OK" || say "digest $1 FAILED"; }

say "==== run_queue_night3 start (pid $$) ===="
# safety: ensure the eval-scoped config is applied (idempotent; backup already exists).
( cd "$HARNESS" && uv run eval_config_scope.py strip >> "$QLOG" 2>&1 ) || true

for M in katdev qwopus ornith; do
  say "==== model $M : run_model start ===="
  bash "$HARNESS/run_model.sh" "$M" >> "$QLOG" 2>&1
  rc=$?
  say "==== model $M : run_model exited rc=$rc -> digest ===="
  digest "$M"
done

say "==== run_queue_night3 COMPLETE ===="
touch "$RESULTS/DONE__QUEUE.marker"
# restore also fires via trap on exit; call explicitly so the marker reflects restored state.
restore_config
say "config restored; queue done"
