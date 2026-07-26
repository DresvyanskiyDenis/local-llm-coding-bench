#!/usr/bin/env bash
# serving_watchdog.sh — safety net for the dead-man state serving_mode.sh cannot
# see: eval mode left ON after whatever agent/process was using it is gone.
#
# THE INCIDENT (2026-07-26, ~20:53-01:00): an agent ran `serving_mode.sh eval`,
# took :8888 for a manual test, and died mid-run when the account hit its usage
# limit. Nothing restored daily mode. For ~4h the machine sat with
# .serving_mode=eval, nothing on :8888 or :8899, no llama-swap process, and the
# launchd job unloaded — and Denis's OpenCode fleet was silently down the whole
# time. serving_mode.sh's clear_port() guard stops *accidental* killing of
# llama-swap; it does nothing about *deliberate* stopping without restart. A
# guard is not an owner, and an agent that dies mid-run owns nothing. This
# script is the owner of last resort.
#
# WHAT COUNTS AS "DEAD-MAN":
#   .serving_mode says eval, AND nothing is listening on :8888, AND there is no
#   eval run in progress. All three, or we do nothing (see "REFUSE LOUDLY" below).
#
# THE HARD PART: telling a real gap from a between-config gap. During a real
# orchestrate.py run (see ../orchestrate.py, ../run_model.sh, ops/watchdog.sh),
# :8888 goes quiet on *every* model swap — unload() clears the port, then
# serve_config() clears it again and waits up to 300s (wait_for_ready's
# timeout) for the new model to answer. That is expected and must NOT trigger
# a restore mid-run. Read from the code, not guessed:
#
#   1. orchestrate.py is launched as `uv run orchestrate.py --resume ...`
#      (run_model.sh line: `caffeinate -ims env PYTHONUNBUFFERED=1 uv run
#      orchestrate.py --resume --only "$MODEL" >> "$ORCH_LOG" 2>&1 &`) and stays
#      alive for the ENTIRE per-model run — serve, probe, smoke, every unit,
#      unload — one long-lived process, not one process per config. So "is
#      there a live orchestrate.py --resume process" is a direct, high-
#      confidence signal of "mid-run", regardless of which phase it's in.
#      This is the exact pattern ops/watchdog.sh already keys off of
#      (`orch_pid(){ pgrep -f "orchestrate.py --resume --only ${MODEL}"; }`) —
#      not a new idea, the codebase's own janitor already trusts this signal.
#      BUT orchestrate.py is not the only eval-mode owner: serving_mode.sh's
#      OWN header says so ("eval — nobody owns :8888; orchestrate.py /
#      run_ifeval.py / run_bcb.py take it and serve ONE model"), and both
#      external adapters import serve_config()/unload() straight from
#      orchestrate.py (run_ifeval.py's run_one_config(), run_bcb.py's
#      run_config()) rather than reimplementing the serve lifecycle — so they
#      produce the exact same port-free windows orchestrate.py does, under a
#      different process name. CAUGHT LIVE while writing this: the machine was
#      mid a `uv run eval/external/bigcodebench/run_bcb.py --only opus__q4
#      --limit 10` at the time, and a first draft matching only
#      `orchestrate.py --resume` misclassified that as DEADMAN. Fixed by
#      matching all three: `orchestrate\.py.*--resume` plus a generic
#      `eval/external/[^ ]+/run_[A-Za-z_]+\.py`, which covers today's two
#      adapters and any future one built on the same naming convention without
#      another hardcoded name.
#   2. As corroboration (in case the process match somehow misses): recent
#      writes under results/ or runs/. ops/watchdog.sh's own `progress_sig()`
#      already treats manifest line count + orch-log bytes + newest rundir
#      mtime as "the run is alive" — this script reuses that idea, simplified
#      to "was anything relevant touched in the last N minutes":
#      results/manifest.jsonl (appended per finished unit),
#      results/logs/{orch__*,*serve*,watchdog__*,queue*}.log (orchestrate's
#      own log, EITHER per-config serve log — orchestrate.py's serve__<name>.log
#      or run_ifeval.py's ifeval_serve__<name>.log — the janitor's 60s
#      heartbeat, and run_queue*.sh's queue log), and runs/<unit>/driver.log.
#      NOT covered by this fallback: run_bcb.py's own serve.log, which lives
#      under eval/external/bigcodebench/_gen/, outside results/ and runs/
#      entirely — that adapter relies on signal (1), the process check, not
#      this one.
#
#   Worst-case legitimate port-free window, from reading serve_config()/
#   unload()/clear_port(): unload's own clear_port (<=15s wait + kill) + the
#   next config's clear_port (<=15s) + wait_for_ready's up-to-300s cold-load
#   timeout + speed_probe + smoke (a couple more minutes) — call it 6-10
#   minutes even when a config is slow or briefly fails before the next one's
#   ready-wait starts. --grace-min defaults to 20 to leave real margin above
#   that, while staying two orders of magnitude below the 4h the real incident
#   ran undetected.
#
#   CONFIDENCE: the process-liveness check (1) is the strong signal for
#   orchestrate.py specifically — it is the same pattern ops/watchdog.sh
#   already relies on in production, so if it is wrong, that script is already
#   wrong the same way. The two run_*.py adapters are matched by path shape
#   rather than an established precedent, so that half is new and less
#   battle-tested than the orchestrate.py half, even though it was validated
#   against a real live run while this script was written (see above) — a
#   fourth adapter with a different directory layout would slip past it. The
#   mtime fallback (2) is a heuristic with a hand-picked threshold; it is
#   there so a missed process match doesn't turn into a false "confirmed
#   dead-man", not as the primary signal, and it does NOT cover run_bcb.py at
#   all (see above). Both (1) and (2) must be absent before this script acts —
#   biased toward doing nothing, per the brief: never act to make room, refuse
#   loudly in every ambiguous case. This whole section is the part most likely
#   to be wrong; if a run shape shows up that neither signal catches (a new
#   wrong; if a run shape shows up that neither signal catches (a new
#   orchestrator that isn't `orchestrate.py --resume` and touches none of the
#   watched paths), you will see a false DEADMAN classification — check the
#   log and --check-only before trusting an unattended restore in that case.
#
# REFUSE LOUDLY in every other case (matches serving_mode.sh's own rule: no
# killing to make room, ever):
#   - .serving_mode=daily but nothing on :8888          -> report, don't act
#     (llama-swap may have crashed; that's a different problem, not this one)
#   - .serving_mode=daily but a NON-llama-swap listener  -> report, don't act
#     (exactly serving_mode.sh's existing guard's territory)
#   - .serving_mode=eval but llama-swap is on :8888      -> report, don't act
#     (shouldn't happen; don't guess what it means)
#   - .serving_mode missing/corrupt                      -> report, don't act
#   - eval mode, port free, but a run looks in progress   -> report, don't act
#     (the between-config gap — see above)
#
# RESTORE PATH: on a confirmed dead-man, this script does NOT reimplement
# serving_mode.sh's launchd bootstrap/kickstart dance — it shells out to
# `serving_mode.sh daily`, the same command Denis would type by hand. That
# script already re-verifies (waits for :8888, confirms the listener really
# is llama-swap, dies loud on failure) before it writes state=daily, so this
# script just needs to check its exit code. (serving_mode.sh is intentionally
# NOT sourced: its last line is an unconditional `case "$1" in eval|daily|
# status) ...` dispatch with no "am I sourced" guard, and it has its own
# `set -euo pipefail`. Sourcing it would run that dispatch against whatever
# $1 this script happened to have, and would leak `set -e` into this script's
# shell — both wrong. Invoking it as a subprocess is the safe form of reuse.)
#
# WHY BASH, NOT PYTHON: this script's entire job is asking the OS three
# questions (who's on this port, is that pid this process, is that launchd
# job loaded) and comparing timestamps — exactly what serving_mode.sh and
# ops/watchdog.sh already do, in the same idiom, on the same machine. There is
# no data processing here that would benefit from Python; matching the
# sibling scripts' language keeps this readable next to them.
#
# TESTING: state-detection logic (`classify`) is exercised by
# serving_watchdog_selftest.sh against synthesized inputs under $TMPDIR — see
# that file. This script is guarded (see the bottom) so it can be sourced by
# the test file without running main() or touching the live machine.
#
# DISABLED BY DEFAULT / OPT-IN — nothing loads this automatically. To arm it:
#   cp eval/harness/ops/com.user.serving-watchdog.plist.template \
#      ~/Library/LaunchAgents/com.user.serving-watchdog.plist
#   launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.user.serving-watchdog.plist
# To check whether it's loaded:
#   launchctl print gui/$(id -u)/com.user.serving-watchdog >/dev/null 2>&1 && echo loaded || echo "not loaded"
# To disable it again:
#   launchctl bootout gui/$(id -u)/com.user.serving-watchdog
#   rm ~/Library/LaunchAgents/com.user.serving-watchdog.plist   # optional, only if you want it gone for good
# Manual, no-side-effect check any time (this is the mode to run by hand):
#   eval/harness/ops/serving_watchdog.sh --check-only
#
# Usage:
#   serving_watchdog.sh [--check-only] [--grace-min N] [--log PATH] [--help]

set -euo pipefail

PORT=8888
LABEL="com.user.llama-swap"
DOMAIN="gui/$(id -u)"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HARNESS_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
EVAL_DIR="$(cd "$HARNESS_DIR/.." && pwd)"
STATE_FILE="$SCRIPT_DIR/.serving_mode"
SERVING_MODE="$SCRIPT_DIR/serving_mode.sh"
RESULTS_DIR="$EVAL_DIR/results"
RUNS_DIR="$EVAL_DIR/runs"
LOG_FILE="$SCRIPT_DIR/serving_watchdog.log"
LOCK_DIR="${TMPDIR:-/var/tmp}/com.user.serving-watchdog.lock"
GRACE_MIN_DEFAULT=20

CHECK_ONLY=0
GRACE_MIN="$GRACE_MIN_DEFAULT"

usage() {
  cat <<'EOF'
usage: serving_watchdog.sh [--check-only] [--grace-min N] [--log PATH] [--help]

Detects the eval-mode dead-man state (.serving_mode=eval, :8888 quiet, no eval
run in progress) and restores daily mode via `serving_mode.sh daily`.

  --check-only    report the state it would act on; never restores anything.
  --grace-min N   minutes of results/runs inactivity that still count as
                   "mid-run" before declaring dead-man (default 20 — see the
                   header comment for why that comfortably covers a
                   between-config gap). Only matters when no eval-mode-owner
                   process is found; the process check is the primary signal.
  --log PATH      event log path (default: ops/serving_watchdog.log).

Disabled by default: see the header comment of this file for the exact
enable/disable commands and the launchd plist template.
EOF
}

die() { echo "ERROR: $*" >&2; exit 1; }

# --- primitives (deliberately duplicated from serving_mode.sh — read-only
# subset only; see header comment for why this is not sourced) --------------

port_pids() { lsof -nP -iTCP:"$PORT" -sTCP:LISTEN -t 2>/dev/null || true; }
pid_comm() { ps -p "$1" -o comm= 2>/dev/null | sed 's|.*/||' || true; }
pid_cmd()  { ps -p "$1" -o command= 2>/dev/null || true; }
svc_loaded() { launchctl print "$DOMAIN/$LABEL" >/dev/null 2>&1; }

llama_swap_on_port() {
  local pid
  for pid in $(port_pids); do
    case "$(pid_comm "$pid")" in
      llama-swap*) echo "$pid"; return 0 ;;
    esac
  done
  return 1
}

read_state() { [ -f "$STATE_FILE" ] && cut -f1 < "$STATE_FILE" || echo "unknown"; }

# --- dead-man vs between-config-gap detection -------------------------------

# A live process for any of the THREE documented eval-mode owners — not just
# orchestrate.py. serving_mode.sh's own header names all three: "eval —
# nobody owns :8888; orchestrate.py / run_ifeval.py / run_bcb.py take it and
# serve ONE model". CONFIRMED LIVE 2026-07-26 while writing this: the machine
# was mid a `run_bcb.py --only opus__q4 --limit 10` run (port briefly free
# between its own serve_config()/unload() calls, imported straight from
# orchestrate.py — see run_bcb.py's run_config() and run_ifeval.py's
# run_one_config(), both of which call orchestrate.serve_config/unload
# directly rather than reimplementing them) and a first draft of this pattern
# that matched only `orchestrate.py --resume` produced a FALSE DEADMAN against
# that exact live state. The pattern below matches orchestrate.py by its
# --resume flag (ops/watchdog.sh's own orch_pid() precedent) and the two
# external adapters generically by their eval/external/<suite>/run_*.py shape,
# so a future third adapter following the same naming convention is caught
# without needing another hardcoded name.
orchestrator_pids() {
  pgrep -f 'orchestrate\.py.*--resume|eval/external/[^ ]+/run_[A-Za-z_]+\.py' 2>/dev/null || true
}

# First path (if any) under results/ or runs/ touched within the last $1
# minutes that would only be written to by a live run. Fallback corroboration
# for when the process match above is empty. Deliberately generous (*serve*,
# not just serve__*): orchestrate.py's own per-config log is
# results/logs/serve__<name>.log, but run_ifeval.py's is
# results/logs/ifeval_serve__<name>.log — same directory, different prefix.
# (run_bcb.py's serve.log lives under eval/external/bigcodebench/_gen/, outside
# results/ and runs/ entirely, and its own generation/eval logs go wherever the
# caller redirected stdout — neither is reachable from here; that adapter is
# covered by the process check above, not this fallback.)
recent_activity_file() {
  local mins="$1" hit=""
  hit="$(find "$RESULTS_DIR" -maxdepth 2 -type f \
         \( -name 'manifest.jsonl' -o -name 'orch__*.log' -o -name '*serve*.log' \
            -o -name 'watchdog__*.log' -o -name 'queue*.log' \) \
         -mmin -"$mins" -print 2>/dev/null | head -1)"
  if [ -z "$hit" ]; then
    hit="$(find "$RUNS_DIR" -maxdepth 2 -type f -name 'driver.log' -mmin -"$mins" -print 2>/dev/null | head -1)"
  fi
  echo "$hit"
}

# Prints "STATE|live_description|recorded=<mode>|detail" — see header for the
# full state list. Never mutates anything.
classify() {
  local grace="$1"
  local recorded live_desc detail state swap_pid pid orch act

  recorded="$(read_state)"

  if swap_pid=$(llama_swap_on_port); then
    live_desc="daily-active (llama-swap pid $swap_pid on :$PORT)"
    case "$recorded" in
      daily) state="HEALTHY_DAILY"; detail="llama-swap pid $swap_pid serving :$PORT, mode file agrees" ;;
      eval)  state="AMBIGUOUS_EVAL_SWAP"; detail="mode file says eval but llama-swap (pid $swap_pid) is on :$PORT" ;;
      *)     state="AMBIGUOUS_UNKNOWN_MODE"; detail="mode file unreadable/unknown ('$recorded') while llama-swap pid $swap_pid holds :$PORT" ;;
    esac
  elif [ -n "$(port_pids)" ]; then
    pid="$(port_pids | head -1)"
    live_desc="eval-serving (:$PORT held by pid $pid, not llama-swap: $(pid_cmd "$pid"))"
    case "$recorded" in
      eval)  state="HEALTHY_EVAL"; detail="non-llama-swap listener pid $pid on :$PORT, mode file agrees" ;;
      daily) state="AMBIGUOUS_DAILY_NONSWAP"; detail="mode file says daily but pid $pid ($(pid_cmd "$pid")) holds :$PORT and is not llama-swap" ;;
      *)     state="AMBIGUOUS_UNKNOWN_MODE"; detail="mode file unreadable/unknown ('$recorded') while pid $pid holds :$PORT" ;;
    esac
  else
    live_desc="port-free (:$PORT has no listener)"
    case "$recorded" in
      daily)
        state="AMBIGUOUS_DAILY_FREE"
        detail="mode file says daily but nothing is listening on :$PORT — llama-swap may be down; this is not the dead-man case this script owns"
        ;;
      eval)
        orch="$(orchestrator_pids | tr '\n' ' ' | sed 's/ *$//')"
        if [ -n "$orch" ]; then
          state="GAP_BETWEEN_CONFIGS"
          detail="port free but an eval-mode owner is alive (pid(s): $orch) — between-config gap, not dead-man"
        else
          act="$(recent_activity_file "$grace")"
          if [ -n "$act" ]; then
            state="GAP_BETWEEN_CONFIGS"
            detail="port free, no eval-mode-owner process, but '$act' was modified within ${grace}m — treating as gap, not dead-man"
          else
            state="DEADMAN"
            detail="port free, no eval-mode-owner process (orchestrate.py/run_ifeval.py/run_bcb.py), no results/runs activity within ${grace}m — confirmed dead-man"
          fi
        fi
        ;;
      *)
        state="AMBIGUOUS_UNKNOWN_MODE"
        detail="mode file unreadable/unknown ('$recorded') and :$PORT is free — cannot infer intent"
        ;;
    esac
  fi

  echo "${state}|${live_desc}|recorded=${recorded}|${detail}"
}

# --- logging + action -------------------------------------------------------

log_event() { printf '%s\t%s\t%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$1" "$2" >> "$LOG_FILE"; }

parse_args() {
  while [ $# -gt 0 ]; do
    case "$1" in
      --check-only) CHECK_ONLY=1; shift ;;
      --grace-min) GRACE_MIN="${2:?--grace-min needs a value}"; shift 2 ;;
      --log) LOG_FILE="${2:?--log needs a path}"; shift 2 ;;
      -h|--help) usage; exit 0 ;;
      *) echo "unknown arg: $1" >&2; usage >&2; exit 2 ;;
    esac
  done
}

main() {
  parse_args "$@"

  # Single-flight: a slow `find` over a big runs/ tree must never overlap with
  # a restore action still in flight from the previous invocation.
  if ! mkdir "$LOCK_DIR" 2>/dev/null; then
    echo "[serving_watchdog] another instance holds $LOCK_DIR, exiting" >&2
    exit 0
  fi
  trap 'rmdir "$LOCK_DIR" 2>/dev/null || true' EXIT

  local result state detail ts
  result="$(classify "$GRACE_MIN")"
  state="${result%%|*}"
  detail="${result#*|}"
  ts="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

  echo "[serving_watchdog] $ts state=$state"
  echo "[serving_watchdog] $detail"

  case "$state" in
    HEALTHY_DAILY|HEALTHY_EVAL)
      exit 0 ;;
  esac

  # Rule 4: leave a trail for anything other than healthy.
  log_event "$state" "$detail"

  if [ "$state" != "DEADMAN" ]; then
    echo "[serving_watchdog] no action taken (ambiguous or run-in-progress case — report only, per rule 3)"
    exit 0
  fi

  if [ "$CHECK_ONLY" -eq 1 ]; then
    echo "[serving_watchdog] --check-only: would run: $SERVING_MODE daily"
    exit 0
  fi

  echo "[serving_watchdog] DEADMAN confirmed — restoring daily mode via: $SERVING_MODE daily"
  if "$SERVING_MODE" daily >>"$LOG_FILE" 2>&1; then
    log_event "ACTION-TAKEN" "serving_mode.sh daily restored llama-swap on :$PORT"
    echo "[serving_watchdog] restored: llama-swap is back on :$PORT"
  else
    log_event "ACTION-FAILED" "serving_mode.sh daily exited non-zero — machine still down, needs a human"
    echo "[serving_watchdog] RESTORE FAILED — see $LOG_FILE, needs a human" >&2
    exit 1
  fi
}

# Guarded so this file can be sourced (by serving_watchdog_selftest.sh) without
# running main() or touching the live machine.
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  main "$@"
fi
