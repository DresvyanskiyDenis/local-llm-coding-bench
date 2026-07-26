#!/usr/bin/env bash
# serving_watchdog_selftest.sh — exercises serving_watchdog.sh's classify()
# against synthesized inputs under $TMPDIR. Touches no real port, process, or
# launchd job: it sources serving_watchdog.sh (safe — that file is guarded so
# sourcing it does not run main()) and then overrides the three functions that
# hit live system state (port_pids/llama_swap_on_port, orchestrator_pids) with
# fakes, per scenario, while pointing RESULTS_DIR/RUNS_DIR/STATE_FILE at a
# scratch dir under $TMPDIR (never /tmp).
#
# Run: bash eval/harness/ops/serving_watchdog_selftest.sh

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORK="$(mktemp -d "${TMPDIR:-/var/tmp}/serving_watchdog_selftest.XXXXXX")"
trap 'rm -rf "$WORK"' EXIT

# shellcheck source=/dev/null
source "$SCRIPT_DIR/serving_watchdog.sh"

# Redirect all paths the real script would touch into the scratch dir.
STATE_FILE="$WORK/.serving_mode"
RESULTS_DIR="$WORK/results"
RUNS_DIR="$WORK/runs"
mkdir -p "$RESULTS_DIR" "$RUNS_DIR"

TOTAL=0
FAILED=0

assert_state() {
  local desc="$1" expected="$2" grace="${3:-20}"
  local actual
  actual="$(classify "$grace")"
  actual="${actual%%|*}"
  TOTAL=$((TOTAL + 1))
  if [ "$actual" = "$expected" ]; then
    echo "ok   - $desc"
  else
    echo "FAIL - $desc: expected $expected, got $actual"
    FAILED=$((FAILED + 1))
  fi
}

set_mode() { printf '%s\t%s\n' "$1" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" > "$STATE_FILE"; }
clear_results() { rm -rf "${RESULTS_DIR:?}"/* "${RUNS_DIR:?}"/* 2>/dev/null; }

# --- scenario A: healthy daily ----------------------------------------------
set_mode daily
port_pids() { echo "111"; }
llama_swap_on_port() { echo "111"; return 0; }
orchestrator_pids() { echo ""; }
assert_state "healthy daily (llama-swap on :8888)" "HEALTHY_DAILY"

# --- scenario B: healthy eval (a real eval server actively serving) --------
set_mode eval
port_pids() { echo "222"; }
llama_swap_on_port() { return 1; }
assert_state "healthy eval (non-llama-swap listener, mode=eval)" "HEALTHY_EVAL"

# --- scenario C: ambiguous — daily recorded, non-swap listener -------------
set_mode daily
port_pids() { echo "333"; }
llama_swap_on_port() { return 1; }
assert_state "ambiguous: mode=daily but non-llama-swap listener" "AMBIGUOUS_DAILY_NONSWAP"

# --- scenario D: ambiguous — daily recorded, port free ----------------------
set_mode daily
port_pids() { echo ""; }
llama_swap_on_port() { return 1; }
assert_state "ambiguous: mode=daily but nothing listening" "AMBIGUOUS_DAILY_FREE"

# --- scenario E: ambiguous — eval recorded, llama-swap actually on the port -
set_mode eval
port_pids() { echo "444"; }
llama_swap_on_port() { echo "444"; return 0; }
assert_state "ambiguous: mode=eval but llama-swap is on :8888" "AMBIGUOUS_EVAL_SWAP"

# --- scenario F: between-config gap via live orchestrate.py process --------
set_mode eval
port_pids() { echo ""; }
llama_swap_on_port() { return 1; }
orchestrator_pids() { echo "5555"; }
clear_results
assert_state "gap: port free but orchestrate.py --resume is alive" "GAP_BETWEEN_CONFIGS"

# --- scenario G: between-config gap via recent file activity (no process) --
set_mode eval
port_pids() { echo ""; }
llama_swap_on_port() { return 1; }
orchestrator_pids() { echo ""; }
clear_results
touch "$RESULTS_DIR/manifest.jsonl"   # mtime = now
assert_state "gap: port free, no process, but manifest.jsonl just touched" "GAP_BETWEEN_CONFIGS"

# --- scenario H: confirmed dead-man — nothing, nothing, nothing ------------
set_mode eval
port_pids() { echo ""; }
llama_swap_on_port() { return 1; }
orchestrator_pids() { echo ""; }
clear_results
assert_state "deadman: eval mode, port free, no process, no recent files" "DEADMAN"

# --- scenario I: stale activity outside the grace window is NOT a gap ------
set_mode eval
port_pids() { echo ""; }
llama_swap_on_port() { return 1; }
orchestrator_pids() { echo ""; }
clear_results
touch "$RESULTS_DIR/manifest.jsonl"
# back-date it well outside a 1-minute grace window. `touch -t` takes its
# argument in LOCAL time (BSD touch has no UTC form for -t), so this must be
# built with local-time `date`, NOT `date -u` — mixing the two silently
# shifts the file by the local UTC offset and breaks the -mmin comparison.
old_stamp="$(date -v-1H +%Y%m%d%H%M.%S 2>/dev/null || date -d '1 hour ago' +%Y%m%d%H%M.%S)"
touch -t "$old_stamp" "$RESULTS_DIR/manifest.jsonl"
assert_state "deadman: manifest.jsonl exists but is 1h stale, grace=1m" "DEADMAN" 1

# --- scenario J: same file, inside a generous grace window -> gap ----------
assert_state "gap: same 1h-stale manifest.jsonl, grace=120m still covers it" "GAP_BETWEEN_CONFIGS" 120

# --- scenario K: unknown/missing mode file, port free -----------------------
rm -f "$STATE_FILE"
port_pids() { echo ""; }
llama_swap_on_port() { return 1; }
orchestrator_pids() { echo ""; }
clear_results
assert_state "ambiguous: mode file missing, port free" "AMBIGUOUS_UNKNOWN_MODE"

# --- scenario L: driver.log under runs/ counts as activity too -------------
set_mode eval
port_pids() { echo ""; }
llama_swap_on_port() { return 1; }
orchestrator_pids() { echo ""; }
clear_results
mkdir -p "$RUNS_DIR/some_unit_id"
touch "$RUNS_DIR/some_unit_id/driver.log"
assert_state "gap: port free, no process, but runs/*/driver.log just touched" "GAP_BETWEEN_CONFIGS"

# --- scenario M: real orchestrator_pids() (not stubbed) against a synthetic -
# `eval/external/.../run_*.py` command line — regression test for the exact
# bug caught live against dnk while writing this script: a first draft that
# only matched `orchestrate.py --resume` misclassified a live run_bcb.py run
# as DEADMAN. Runs the REAL function (not a stub) against a fake process tree
# is not practical in bash without root, so this instead unit-tests the regex
# itself via `grep -E`, which is exactly what pgrep -f evaluates internally.
PATTERN='orchestrate\.py.*--resume|eval/external/[^ ]+/run_[A-Za-z_]+\.py'
assert_pattern_matches() {
  local desc="$1" line="$2"
  TOTAL=$((TOTAL + 1))
  if echo "$line" | grep -Eq "$PATTERN"; then
    echo "ok   - $desc"
  else
    echo "FAIL - $desc: pattern did not match '$line'"
    FAILED=$((FAILED + 1))
  fi
}
assert_pattern_no_match() {
  local desc="$1" line="$2"
  TOTAL=$((TOTAL + 1))
  if echo "$line" | grep -Eq "$PATTERN"; then
    echo "FAIL - $desc: pattern unexpectedly matched '$line'"
    FAILED=$((FAILED + 1))
  else
    echo "ok   - $desc"
  fi
}
assert_pattern_matches "orchestrator regex matches orchestrate.py --resume (run_model.sh shape)" \
  "caffeinate -ims env PYTHONUNBUFFERED=1 uv run orchestrate.py --resume --only qwen"
assert_pattern_matches "orchestrator regex matches run_bcb.py (the live false-negative caught 2026-07-26)" \
  "/Users/denisdresvyanskiy/.cache/uv/environments-v2/run-bcb-xyz/bin/python3 eval/external/bigcodebench/run_bcb.py --only opus__q4 --limit 10"
assert_pattern_matches "orchestrator regex matches run_ifeval.py" \
  "uv run eval/external/ifeval/run_ifeval.py --only opus --limit 20"
assert_pattern_no_match "orchestrator regex does NOT match an unrelated python process" \
  "/opt/homebrew/bin/python3 -m http.server 8791"
assert_pattern_no_match "orchestrator regex does NOT match orchestrate.py --dry-run (never holds the port)" \
  "uv run orchestrate.py --dry-run"

echo
echo "$((TOTAL - FAILED))/$TOTAL passed"
[ "$FAILED" -eq 0 ]
