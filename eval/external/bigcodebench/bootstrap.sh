#!/usr/bin/env bash
# Bootstrap the BigCodeBench evaluation venv (Round 2, Phase 0 step 4).
#
# WHY THIS IS NOT `uv pip install bigcodebench`:
#   bigcodebench==0.2.5 declares `vllm` as a HARD dependency, and vllm has no arm64/macOS
#   wheel. vllm is imported LAZILY inside bigcodebench/provider/__init__.py::make_model,
#   only when backend == "vllm" — so `--no-deps` + a curated runtime set is sufficient for
#   the `--backend openai` path we use.
#
# WHY THE PINS ARE STRIPPED:
#   Requirements/requirements-eval.txt pins numpy==1.21.2, numba==0.55.0, keras==2.11.0,
#   gensim==4.3.2, tensorflow==2.11.0 ... — versions with no Apple-Silicon wheels.
#   DECIDED 2026-07-25 (IMPLEMENTATION_PLAN.md §1): relaxed pins + local execution +
#   an honest env-health number. Consequence: BCB pass@1 is a WITHIN-FLEET number,
#   NOT comparable to the public BigCodeBench leaderboard.
#
# Re-runnable: existing .venv is reused unless --recreate is passed.
# Writes eval/external/bigcodebench/install_report.json recording what actually installed.
#
# Usage:
#   bash eval/external/bigcodebench/bootstrap.sh [--recreate]

set -euo pipefail

BCB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$BCB_DIR/.venv"
WORK="$BCB_DIR/_work"
PY_VERSION="3.12"
BCB_VERSION="0.2.5"
REQ_EVAL="$BCB_DIR/requirements-eval-${BCB_VERSION}.txt"
REQ_RELAXED="$WORK/requirements-eval-relaxed.txt"
REPORT="$BCB_DIR/install_report.json"

RECREATE=0
for arg in "$@"; do
  case "$arg" in
    --recreate) RECREATE=1 ;;
    *) echo "unknown arg: $arg" >&2; exit 2 ;;
  esac
done

command -v uv >/dev/null || { echo "FATAL: uv not on PATH (uv only — never pip, never poetry)" >&2; exit 1; }
[ -f "$REQ_EVAL" ] || { echo "FATAL: missing $REQ_EVAL" >&2; exit 1; }

mkdir -p "$WORK"

# ---------------------------------------------------------------- 1. venv
if [ "$RECREATE" = "1" ] && [ -d "$VENV" ]; then
  echo "==> removing existing venv (--recreate)"
  rm -rf "$VENV"
fi
if [ ! -x "$VENV/bin/python" ]; then
  echo "==> creating venv at $VENV (python $PY_VERSION)"
  uv venv --python "$PY_VERSION" "$VENV"
else
  echo "==> reusing existing venv at $VENV"
fi
VPY="$VENV/bin/python"

pipi() { uv pip install --python "$VPY" "$@"; }

# ---------------------------------------------------------------- 2. bigcodebench, no deps
echo "==> installing bigcodebench==${BCB_VERSION} --no-deps"
pipi --no-deps "bigcodebench==${BCB_VERSION}"

# ---------------------------------------------------------------- 3. curated runtime set
# Exactly what the --backend openai generate path + the local-execution evaluate path
# import. evaluate.py imports gradio_client AND e2b at module top level, so both are
# required even though we never use the remote executors.
CURATED=(
  openai datasets transformers tqdm termcolor numpy rich appdirs
  fire multipledispatch pqdm tempdir tree_sitter tree-sitter-python
  wget gradio-client e2b httpx
)
echo "==> installing curated runtime set (${#CURATED[@]} packages)"
pipi "${CURATED[@]}"

# ---------------------------------------------------------------- 4. relaxed eval requirements
echo "==> generating pin-stripped requirements at $REQ_RELAXED"
# Strip every version specifier; drop comments, blank lines and duplicates (the upstream
# file lists requests/Requests, statsmodels and xlrd twice).
sed -e 's/#.*$//' -e 's/[[:space:]]*$//' "$REQ_EVAL" \
  | sed -e 's/[=<>!~].*$//' \
  | grep -v '^$' \
  | tr 'A-Z' 'a-z' \
  | sort -u > "$REQ_RELAXED"
echo "    $(wc -l < "$REQ_RELAXED" | tr -d ' ') unique packages after stripping pins"

echo "==> bulk install attempt (single resolution -> mutually consistent versions)"
BULK_OK=1
pipi -r "$REQ_RELAXED" || BULK_OK=0

FAILED_FILE="$WORK/failed_packages.txt"
: > "$FAILED_FILE"

if [ "$BULK_OK" = "0" ]; then
  echo "==> bulk resolution FAILED; falling back to per-package installs"
  echo "    (records every package that cannot install at all)"
  while read -r pkg; do
    [ -z "$pkg" ] && continue
    if pipi "$pkg" >/dev/null 2>&1; then
      printf '  ok    %s\n' "$pkg"
    else
      printf '  FAIL  %s\n' "$pkg"
      echo "$pkg" >> "$FAILED_FILE"
    fi
  done < "$REQ_RELAXED"
else
  echo "==> bulk install succeeded"
fi

# ---------------------------------------------------------------- 5. verify no vllm import
echo "==> verifying bigcodebench imports without vllm"
"$VPY" - <<'PYEOF'
import importlib, sys
for mod in ("bigcodebench.generate", "bigcodebench.evaluate", "bigcodebench.provider"):
    importlib.import_module(mod)
assert "vllm" not in sys.modules, "vllm was imported eagerly -- the --no-deps premise is wrong"
print("    OK: generate + evaluate import, vllm NOT in sys.modules")
PYEOF

# ---------------------------------------------------------------- 6. install report
echo "==> writing $REPORT"
"$VPY" - "$REQ_EVAL" "$REQ_RELAXED" "$FAILED_FILE" "$REPORT" "$BCB_VERSION" <<'PYEOF'
import json, platform, sys, re
from importlib.metadata import distributions
from datetime import datetime, timezone
from pathlib import Path

req_eval, req_relaxed, failed_file, report, bcb_version = sys.argv[1:6]

# uv venvs have no pip; read the installed set from the metadata directly.
installed = {}
for dist in distributions():
    name = (dist.metadata["Name"] or "").strip().lower().replace("_", "-")
    if name:
        installed[name] = dist.version

pinned = {}
for line in Path(req_eval).read_text().splitlines():
    line = line.split("#")[0].strip()
    if not line:
        continue
    m = re.match(r"^([A-Za-z0-9_.\-]+)\s*==\s*(.+)$", line)
    if m:
        pinned[m.group(1).lower().replace("_", "-")] = m.group(2)
    else:
        pinned[line.lower().replace("_", "-")] = None

failed = [l.strip() for l in Path(failed_file).read_text().splitlines() if l.strip()] \
    if Path(failed_file).exists() else []

relaxed = {}
missing = []
for name, want in sorted(pinned.items()):
    got = installed.get(name)
    if got is None:
        missing.append(name)
    elif want is not None and got != want:
        relaxed[name] = {"pinned": want, "resolved": got}

obj = {
    "bigcodebench_version": bcb_version,
    "install_strategy": "uv pip install --no-deps bigcodebench + curated runtime set + "
                        "requirements-eval.txt with pins stripped",
    "python": sys.version.split()[0],
    "platform": f"{platform.system()}-{platform.machine()}",
    "n_requirements_eval": len(pinned),
    "n_installed": len(pinned) - len(missing),
    "n_pins_relaxed": len(relaxed),
    "pins_relaxed": relaxed,
    "not_installed": sorted(missing),
    "explicit_install_failures": failed,
    "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
}
Path(report).write_text(json.dumps(obj, indent=2) + "\n")
print(f"    {obj['n_installed']}/{obj['n_requirements_eval']} requirements-eval packages present; "
      f"{obj['n_pins_relaxed']} pins relaxed; {len(missing)} missing")
PYEOF

echo
echo "DONE. Next: $VPY $BCB_DIR/env_health.py"
echo "REMINDER: relaxed pins => BCB pass@1 is WITHIN-FLEET only, not leaderboard-comparable."
