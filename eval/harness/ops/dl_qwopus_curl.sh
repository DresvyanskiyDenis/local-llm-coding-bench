#!/bin/bash
# dl_qwopus_curl.sh — robust, resumable download of the qwopus Q5_K_M GGUF.
# hf download wedges on the Xet CDN (CLOSE_WAIT) and restarts from 0 on kill,
# so it can never finish a flaky transfer. curl -L -C - against the stable
# resolve URL re-signs a fresh Xet redirect each attempt and RESUMES from the
# current byte offset (verified: mid-file ranged GET -> HTTP 206). So every
# connection drop just continues; progress is never lost. Launch DETACHED.
set -u
REPO_ROOT="${REPO_ROOT:-$(cd "$(dirname "$0")/../../.." && pwd)}"
URL="https://huggingface.co/Jackrong/Qwopus3.6-35B-A3B-Coder-MTP-GGUF/resolve/main/Qwopus3.6-35B-A3B-Coder-MTP-Q5_K_M.gguf"
SNAP="$HOME/.cache/huggingface/hub/models--Jackrong--Qwopus3.6-35B-A3B-Coder-MTP-GGUF/snapshots/6a5663090399e07f669c6f036a6ade65062c96db"
OUT="$SNAP/Qwopus3.6-35B-A3B-Coder-MTP-Q5_K_M.gguf"
EXPECTED=25347531936
RESULTS="$REPO_ROOT/eval/results"
LOG="$RESULTS/logs/qwopus_download.log"
MARK="$RESULTS/DONE__qwopus_download.marker"
mkdir -p "$SNAP" "$RESULTS/logs"
say(){ echo "$(date '+%F %T') curl_dl $*" >> "$LOG"; }
cursize(){ stat -f '%z' "$OUT" 2>/dev/null || echo 0; }

say "==== curl downloader start (pid $$) target=$EXPECTED ===="
attempt=0
while [ "$(cursize)" -lt "$EXPECTED" ]; do
  attempt=$((attempt+1))
  say "attempt $attempt: resuming from $(cursize) bytes"
  # -C - resume; long timeouts; low-speed abort so a dead socket is cut fast
  # and the loop reconnects (rather than hanging like hf did on CLOSE_WAIT).
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
