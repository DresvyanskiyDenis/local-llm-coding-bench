#!/bin/bash
# dl_watchdog.sh — keep the qwopus GGUF download alive until complete.
# The hf CDN drops connections and `hf download` wedges on a CLOSE_WAIT socket
# (observed 2026-07-14): 0 bytes, process sleeping at 0% CPU, never recovers.
# This watchdog detects a stall (no growth for STALL_SECS) and restarts the
# resumable download, then writes a DONE marker when the .incomplete blob is
# gone and the snapshot file is materialised. Launch DETACHED (own session).
set -u
REPO_ROOT="${REPO_ROOT:-$(cd "$(dirname "$0")/../../.." && pwd)}"
HF="${HF:-$HOME/.pyenv/versions/3.12.10/bin/hf}"
REPO=Jackrong/Qwopus3.6-35B-A3B-Coder-MTP-GGUF
FILE=Qwopus3.6-35B-A3B-Coder-MTP-Q5_K_M.gguf
CACHE="$HOME/.cache/huggingface/hub/models--Jackrong--Qwopus3.6-35B-A3B-Coder-MTP-GGUF"
RESULTS="$REPO_ROOT/eval/results"
LOG="$RESULTS/logs/qwopus_download.log"
MARK="$RESULTS/DONE__qwopus_download.marker"
STALL_SECS=${STALL_SECS:-240}     # restart if no growth for 4 min
mkdir -p "$RESULTS/logs"
say(){ echo "$(date '+%F %T') dl_watchdog $*" >> "$LOG"; }

blob(){ find "$CACHE/blobs" -name '*.incomplete' 2>/dev/null | head -1; }
size(){ local b; b=$(blob); [ -n "$b" ] && stat -f '%z' "$b" 2>/dev/null || echo 0; }
dl_alive(){ pgrep -f "hf download $REPO" >/dev/null 2>&1; }
snapshot_file(){ find "$CACHE/snapshots" -name "$FILE" 2>/dev/null | head -1; }

start_dl(){
  say "starting hf download (resumable)"
  nohup "$HF" download "$REPO" "$FILE" >> "$LOG" 2>&1 &
}

say "==== watchdog start (pid $$) ===="
last=$(size); last_change=$(date +%s)
while true; do
  # completion: no .incomplete blob AND the snapshot file exists & is large
  sf=$(snapshot_file)
  if [ -z "$(blob)" ] && [ -n "$sf" ] && [ "$(stat -f '%z' "$sf" 2>/dev/null || echo 0)" -gt 20000000000 ]; then
    say "COMPLETE -> $sf ($(stat -f '%z' "$sf") bytes)"
    { echo "file=$sf"; echo "bytes=$(stat -f '%z' "$sf")"; echo "finished_at=$(date '+%F %T')"; } > "$MARK"
    break
  fi
  if ! dl_alive; then
    say "no downloader running -> (re)start"
    start_dl
    sleep 20; last=$(size); last_change=$(date +%s); continue
  fi
  cur=$(size)
  now=$(date +%s)
  if [ "$cur" -gt "$last" ]; then
    last=$cur; last_change=$now
  elif [ $(( now - last_change )) -ge "$STALL_SECS" ]; then
    say "STALL detected (${STALL_SECS}s no growth at $cur bytes) -> kill+restart"
    pkill -9 -f "hf download $REPO" 2>/dev/null
    sleep 3; start_dl
    sleep 20; last=$(size); last_change=$(date +%s)
  fi
  sleep 30
done
say "==== watchdog done ===="
