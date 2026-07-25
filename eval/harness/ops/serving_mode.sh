#!/usr/bin/env bash
# Switch this machine between the two serving stacks that both want :8888.
#
#   daily  — llama-swap (LaunchAgent com.user.llama-swap) owns :8888 and swaps
#            backends on demand onto :5800+. This is what OpenCode uses day to day.
#   eval   — nobody owns :8888; orchestrate.py / run_ifeval.py / run_bcb.py take it
#            and serve ONE model via ~/bin/unsloth-serve, exactly as round 1 did
#            (IMPLEMENTATION_PLAN.md §3.5, decision of 2026-07-25).
#
# Verified live 2026-07-25: llama-swap IS launchd-managed
#   ~/Library/LaunchAgents/com.user.llama-swap.plist, RunAtLoad=true, KeepAlive=false
# so it is stopped/started through launchctl, not by killing the pid — a bare kill
# would leave the job loaded and let launchd (or the next login) race the eval run
# for the port.
#
# Usage:
#   eval/harness/ops/serving_mode.sh eval     # hand :8888 to the eval harness
#   eval/harness/ops/serving_mode.sh daily    # give :8888 back to llama-swap
#   eval/harness/ops/serving_mode.sh status   # which mode is the machine in
#
# Idempotent in both directions. Records the mode it left the machine in to
# ops/.serving_mode (gitignored) so a crashed night is diagnosable in the morning.
# Fails loud (non-zero + a message saying what to do) rather than half-switching.

set -euo pipefail

LABEL="com.user.llama-swap"
PLIST="$HOME/Library/LaunchAgents/${LABEL}.plist"
DOMAIN="gui/$(id -u)"
PORT=8888
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STATE_FILE="$SCRIPT_DIR/.serving_mode"

die() { echo "ERROR: $*" >&2; exit 1; }
note() { echo "[serving_mode] $*"; }

# --- primitives --------------------------------------------------------------

port_pids() { lsof -nP -iTCP:"$PORT" -sTCP:LISTEN -t 2>/dev/null || true; }

# Identify by command NAME, never by a remembered pid.
pid_comm() { ps -p "$1" -o comm= 2>/dev/null | sed 's|.*/||' || true; }
pid_cmd()  { ps -p "$1" -o command= 2>/dev/null || true; }

llama_server_pids() { pgrep -f 'llama-server' 2>/dev/null || true; }

svc_loaded() { launchctl print "$DOMAIN/$LABEL" >/dev/null 2>&1; }

# Is the :8888 listener llama-swap? Echoes the pid if so.
llama_swap_on_port() {
  local pid
  for pid in $(port_pids); do
    case "$(pid_comm "$pid")" in
      llama-swap*) echo "$pid"; return 0 ;;
    esac
  done
  return 1
}

wait_until() {  # wait_until <timeout_s> <predicate...>
  local timeout=$1; shift
  local deadline=$(( SECONDS + timeout ))
  while (( SECONDS < deadline )); do
    if "$@"; then return 0; fi
    sleep 0.5
  done
  return 1
}

port_free()   { [ -z "$(port_pids)" ]; }
port_taken()  { [ -n "$(port_pids)" ]; }
no_llama_server() { [ -z "$(llama_server_pids)" ]; }

write_state() { printf '%s\t%s\n' "$1" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" > "$STATE_FILE"; }
read_state()  { [ -f "$STATE_FILE" ] && cut -f1 < "$STATE_FILE" || echo "unknown"; }

describe_port() {
  local pid
  for pid in $(port_pids); do
    echo "    :$PORT pid $pid  $(pid_cmd "$pid")"
  done
}

# --- eval --------------------------------------------------------------------

do_eval() {
  if svc_loaded; then
    note "booting out $LABEL from $DOMAIN"
    launchctl bootout "$DOMAIN/$LABEL" 2>/dev/null || true
  else
    note "$LABEL is not loaded in $DOMAIN (already stopped)"
  fi

  # A bare llama-swap started by hand would not be launchd-managed; catch it too.
  local swap_pid
  if swap_pid=$(llama_swap_on_port); then
    note "llama-swap still on :$PORT as pid $swap_pid, sending SIGTERM"
    kill -TERM "$swap_pid" 2>/dev/null || true
  fi

  wait_until 20 port_free || {
    note "port :$PORT still held after 20s:"; describe_port
    die "could not free :$PORT — refusing to hand a contended port to the eval harness"
  }

  # llama-swap's backends (and any orphaned Studio child — see the SERVING SHAPES
  # note in ~/.config/llama-swap/config.yaml: SIGTERM to a Studio parent orphans
  # its llama-server child holding ~20 GB) must be gone, or the eval model has no RAM.
  local leftovers
  leftovers="$(llama_server_pids)"
  if [ -n "$leftovers" ]; then
    note "llama-server still alive after llama-swap stopped: $leftovers — terminating"
    # shellcheck disable=SC2086
    kill -TERM $leftovers 2>/dev/null || true
    wait_until 15 no_llama_server || {
      leftovers="$(llama_server_pids)"
      note "escalating to SIGKILL for: $leftovers"
      # shellcheck disable=SC2086
      kill -KILL $leftovers 2>/dev/null || true
    }
  fi

  wait_until 10 no_llama_server || die "llama-server processes survive: $(llama_server_pids)"
  port_free || die "something re-bound :$PORT"

  write_state eval
  note "MODE=eval — :$PORT is free, no llama-server alive. The harness may take the port."
}

# --- daily -------------------------------------------------------------------

do_daily() {
  # If an eval server still holds the port, say so instead of fighting it: killing
  # a mid-run llama-server would destroy in-flight units.
  local pid
  for pid in $(port_pids); do
    case "$(pid_comm "$pid")" in
      llama-swap*) : ;;
      *) die "…:$PORT is held by pid $pid ($(pid_cmd "$pid")).
       That looks like an eval server still running. Stop the eval run first;
       this script will not kill it." ;;
    esac
  done

  if svc_loaded; then
    note "$LABEL already loaded — kickstarting"
    launchctl kickstart "$DOMAIN/$LABEL" >/dev/null 2>&1 || true
  else
    [ -f "$PLIST" ] || die "$PLIST not found — cannot restore daily mode"
    note "bootstrapping $LABEL from $PLIST"
    launchctl bootstrap "$DOMAIN" "$PLIST" || die "launchctl bootstrap failed for $PLIST"
  fi

  wait_until 30 port_taken || die "llama-swap did not bind :$PORT within 30s (see ~/.unsloth/studio/logs/llama-swap.log)"
  local swap_pid
  swap_pid=$(llama_swap_on_port) || {
    note "…:$PORT is bound but not by llama-swap:"; describe_port
    die "unexpected listener on :$PORT"
  }

  write_state daily
  note "MODE=daily — llama-swap pid $swap_pid is listening on :$PORT. OpenCode has its models."
}

# --- status ------------------------------------------------------------------

do_status() {
  local recorded live swap_pid
  recorded="$(read_state)"
  if swap_pid=$(llama_swap_on_port); then
    live="daily (llama-swap pid $swap_pid on :$PORT)"
  elif port_taken; then
    live="eval-serving (:$PORT held by something that is not llama-swap)"
  else
    live="eval (:$PORT free)"
  fi
  echo "recorded mode : $recorded  ($STATE_FILE)"
  echo "live mode     : $live"
  echo "launchd job   : $(svc_loaded && echo "loaded in $DOMAIN" || echo "not loaded")"
  echo "llama-server  : $(llama_server_pids | tr '\n' ' ' | sed 's/ $//' || true)"
  port_taken && describe_port
  return 0
}

case "${1:-}" in
  eval)   do_eval ;;
  daily)  do_daily ;;
  status) do_status ;;
  *) echo "usage: $(basename "$0") {eval|daily|status}" >&2; exit 2 ;;
esac
