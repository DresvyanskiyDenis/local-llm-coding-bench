#!/bin/bash
# dl_ornith_curl.sh — robust, resumable download of the ornith Q4_K_M GGUF.
# Same rationale as dl_qwopus_curl.sh: hf download wedges on the Xet CDN
# (CLOSE_WAIT) and restarts from 0 on kill; curl -L -C - against the stable
# resolve URL re-signs a fresh Xet redirect each attempt and RESUMES from the
# current byte offset (HTTP 206), so drops never lose progress. Launch DETACHED.
set -u
REPO_ROOT="${REPO_ROOT:-$(cd "$(dirname "$0")/../../.." && pwd)}"
URL="https://huggingface.co/tashfene/Ornith-1.0-35B-MTP-Q4_K_M-GGUF/resolve/main/ornith-1.0-35b-MTP-graft-Q4_K_M.gguf"
SNAP="$HOME/.cache/huggingface/hub/models--tashfene--Ornith-1.0-35B-MTP-Q4_K_M-GGUF/snapshots/main"
OUT="$SNAP/ornith-1.0-35b-MTP-graft-Q4_K_M.gguf"
EXPECTED=21695616160
RESULTS="$REPO_ROOT/eval/results"
LOG="$RESULTS/logs/ornith_download.log"
MARK="$RESULTS/DONE__ornith_download.marker"
mkdir -p "$SNAP" "$RESULTS/logs"
say(){ echo "$(date '+%F %T') curl_dl $*" >> "$LOG"; }
cursize(){ stat -f '%z' "$OUT" 2>/dev/null || echo 0; }

say "==== curl downloader start (pid $$) target=$EXPECTED ===="
attempt=0
while [ "$(cursize)" -lt "$EXPECTED" ]; do
  attempt=$((attempt+1))
  say "attempt $attempt: resuming from $(cursize) bytes"
  curl -L -C - --fail-with-body \
       --connect-timeout 30 \
       --speed-limit 51200 --speed-time 60 \
       --retry 3 --retry-delay 5 \
       -o "$OUT" "$URL" >> "$LOG" 2>&1
  rc=$?
  say "attempt $attempt: curl rc=$rc size=$(cursize)/$EXPECTED"
  [ "$(cursize)" -ge "$EXPECTED" ] && break
  sleep 5
done

sz=$(cursize)
if [ "$sz" -eq "$EXPECTED" ]; then
  magic=$(head -c 4 "$OUT" 2>/dev/null)
  say "COMPLETE size=$sz magic=$magic"
  { echo "file=$OUT"; echo "bytes=$sz"; echo "magic=$magic"; echo "finished_at=$(date '+%F %T')"; } > "$MARK"
else
  say "ENDED size=$sz != expected $EXPECTED (no marker written)"
fi
say "==== curl downloader done ===="
