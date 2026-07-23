#!/bin/bash
# watchdog.sh <model> — background JANITOR for a running `orchestrate.py --resume --only
# <model>`. It is NOT the completion/wake signal any more: the main loop owns completion
# detection via run_model.sh's own exit + the DONE marker on disk. This script only:
#   (1) reaps orphaned opencode leaks (parent reparented to init == RAM pinned) every loop;
#   (2) force-kills opencode ONLY after STALL_SECS of zero progress — i.e. once the driver's
#       own 900s killpg has demonstrably failed — so a legitimately long inference is never
#       preempted (it always resolves within ~16 min via the driver timeout);
#   (3) writes a heartbeat line every loop, so a *frozen* watchdog is visible in the log
#       (the qwen post-mortem: the old watchdog died silently with no heartbeat trail).
# Exits when orchestrate exits. Kept deliberately cheap — no recursive find/stat (that was
# the most hang-prone call and is gone).
set -u
MODEL="${1:?usage: watchdog.sh <model>}"
REPO_ROOT="${REPO_ROOT:-$(cd "$(dirname "$0")/../../.." && pwd)}"
BASE="$REPO_ROOT/eval"
RESULTS="$BASE/results"; RUNS="$BASE/runs"
LOG="$RESULTS/logs/orch__${MODEL}.log"
WLOG="$RESULTS/logs/watchdog__${MODEL}.log"
STALL_SECS=${STALL_SECS:-1500}   # 25 min > driver 900s + grading + cold-serve margin

ts(){ date '+%F %T'; }
orch_pid(){ pgrep -f "orchestrate.py --resume --only ${MODEL}" | head -1; }

reap_orphans(){
  for p in $(pgrep -f "opencode run" 2>/dev/null); do
    ppid=$(ps -o ppid= -p "$p" 2>/dev/null | tr -d ' ')
    if [ "$ppid" = "1" ]; then
      pgid=$(ps -o pgid= -p "$p" 2>/dev/null | tr -d ' ')
      [ -n "$pgid" ] && kill -KILL -"$pgid" 2>/dev/null && echo "$(ts) reaped orphan opencode pid=$p pgid=$pgid" >> "$WLOG"
    fi
  done
}

kill_opencode(){
  for p in $(pgrep -f "opencode run" 2>/dev/null); do
    pgid=$(ps -o pgid= -p "$p" 2>/dev/null | tr -d ' '); [ -n "$pgid" ] && kill -TERM -"$pgid" 2>/dev/null
  done
  sleep 8
  for p in $(pgrep -f "opencode run" 2>/dev/null); do
    pgid=$(ps -o pgid= -p "$p" 2>/dev/null | tr -d ' '); [ -n "$pgid" ] && kill -KILL -"$pgid" 2>/dev/null
  done
}

# cheap progress signal: manifest line count + orch-log bytes + newest rundir mtime (no recursion)
progress_sig(){
  local m l r rm
  m=$(wc -l < "$RESULTS/manifest.jsonl" 2>/dev/null | tr -d ' ')
  l=$(wc -c < "$LOG" 2>/dev/null | tr -d ' ')
  r=$(ls -dt "$RUNS"/${MODEL}__*/ 2>/dev/null | head -1)
  rm=$(stat -f %m "$r" 2>/dev/null)
  echo "${m}|${l}|${rm}"
}

PID=$(orch_pid)
if [ -z "$PID" ]; then echo "$(ts) no orchestrate for $MODEL; exiting" >> "$WLOG"; exit 0; fi
echo "$(ts) watchdog start model=$MODEL orch_pid=$PID stall=${STALL_SECS}s" >> "$WLOG"

prev=""; last=$(date +%s); beat=0
while kill -0 "$PID" 2>/dev/null; do
  reap_orphans
  sig=$(progress_sig); now=$(date +%s)
  if [ "$sig" != "$prev" ]; then prev="$sig"; last=$now; fi
  stalled=$(( now - last )); beat=$(( beat + 1 ))
  echo "$(ts) heartbeat #$beat stalled=${stalled}s sig=$sig" >> "$WLOG"
  if [ "$stalled" -ge "$STALL_SECS" ]; then
    echo "$(ts) STALL ${stalled}s no-progress — OpenCode hang suspected; killing opencode (model=$MODEL)" >> "$WLOG"
    kill_opencode; reap_orphans; last=$(date +%s)
  fi
  sleep 60
done
echo "$(ts) orchestrate exited (model=$MODEL)" >> "$WLOG"
