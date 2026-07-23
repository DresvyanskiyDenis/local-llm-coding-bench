#!/bin/bash
# ============================================================================
#  Local-LLM coding stack installer  —  Unsloth Studio + OpenCode + Copilot CLI
#  Target: Apple Silicon Mac (M1–M4), 36 GB unified memory, macOS.
#
#  Replicates a day-to-day local-coding setup:
#    • Unsloth Studio  (patched llama.cpp, serves GGUF on :8888)
#    • ~/bin/unsloth-serve  (8-model launcher, one model at a time)
#    • OpenCode         (local-first agentic coding CLI, default = local Qwen3.6)
#    • GitHub Copilot CLI
#
#  USAGE
#    ./install.sh                 interactive: asks [y/N] before every step,
#                                 lets you pick which models to download
#    ./install.sh --auto          non-interactive: does everything automatically
#                                 EXCEPT downloading models (too big/slow to
#                                 assume) and EXCEPT the sudo/login system tweaks
#    ./install.sh --auto --with-system
#                                 same, but ALSO does the GPU-limit (sudo) and
#                                 login-autostart steps
#    ./install.sh --help
#
#  It is IDEMPOTENT: every step detects what is already installed and skips it.
#  Re-running is safe — it only fills in what's missing.
# ============================================================================
set -euo pipefail

# `set -euo pipefail` = stop on any error (-e), on any unset variable (-u), and
# make a failure anywhere in a pipeline fail the whole pipe (-o pipefail).
# It makes the script fail LOUD instead of silently limping on after a broken step.

# ---- command-line flags ----------------------------------------------------
# Two knobs. Everything defaults to the safe/interactive behaviour; the flags
# only make it MORE automatic. We parse them into simple 0/1 variables.
AUTO=0          # 1 = non-interactive ("yes" to every step), set by --auto
WITH_SYSTEM=0   # 1 = also do the sudo/login steps in --auto, set by --with-system
for arg in "$@"; do
  case "$arg" in
    --auto|-y|--yes)  AUTO=1 ;;                       # run unattended
    --with-system)    WITH_SYSTEM=1 ;;                # include GPU-limit + autostart
    -h|--help)
      # Print the big usage banner at the top of this file (lines 2–25),
      # stripping the leading "# " so it reads like plain help text.
      sed -n '2,25p' "$0" | sed 's/^# \{0,1\}//'
      exit 0 ;;
    *) echo "unknown arg: $arg  (see --help)" >&2; exit 2 ;;
  esac
done

# ---- paths we touch (all under your home dir) ------------------------------
# SCRIPT_DIR = the folder THIS script lives in, resolved even if called via a
# relative path or symlink. We need it to find the assets/ folder next to us.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ASSETS="$SCRIPT_DIR/assets"                          # the files we copy into place
OC_DIR="$HOME/.config/opencode"                      # OpenCode config lives here
BIN_DIR="$HOME/bin"                                  # where the launcher goes
HUB="$HOME/.cache/huggingface/hub"                   # HuggingFace model cache
ZSHENV="$HOME/.zshenv"                                # shell env we append to
# Marker lines that fence OUR block inside ~/.zshenv, so re-running the script
# can detect "already added" and never append the block twice.
MARK_BEGIN="# >>> unsloth+opencode team setup >>>"
MARK_END="# <<< unsloth+opencode team setup <<<"

# ---- terminal colours + tiny logging helpers -------------------------------
# `[ -t 1 ]` is true only when stdout is a real terminal (not a pipe/file), so
# we emit colour codes there and plain text otherwise. B=bold DIM=grey G=green
# Y=yellow R=red C=cyan N=reset.
if [ -t 1 ]; then B=$'\033[1m'; DIM=$'\033[2m'; G=$'\033[32m'; Y=$'\033[33m'; R=$'\033[31m'; C=$'\033[36m'; N=$'\033[0m'
else B=""; DIM=""; G=""; Y=""; R=""; C=""; N=""; fi
say()  { printf '%b\n' "$*"; }                                                   # a plain line
hr()   { printf '%b\n' "${DIM}────────────────────────────────────────────────────────────${N}"; }
ok()   { printf '  %b✓%b %s\n' "$G" "$N" "$*"; }                                 # green success
skip() { printf '  %b•%b %s %b(already present — skipped)%b\n' "$C" "$N" "$*" "$DIM" "$N"; }  # idempotent skip
warn() { printf '  %b!%b %s\n' "$Y" "$N" "$*"; }                                 # yellow caution
err()  { printf '  %b✗%b %s\n' "$R" "$N" "$*" >&2; }                             # red error → stderr

# ask "question"  ->  exit status 0 = yes, 1 = no.
# This is the heart of the "ask before every step" behaviour:
#   • in --auto mode it prints the question and auto-answers YES (status 0)
#   • otherwise it prompts [y/N] and reads ONE line; only a literal y/Y = yes.
# We read from /dev/tty (the real keyboard) rather than stdin, so prompting
# still works even if the script itself was piped in.
ask() {
  if [ "$AUTO" -eq 1 ]; then printf '  %b→%b %s %b(auto-yes)%b\n' "$C" "$N" "$1" "$DIM" "$N"; return 0; fi
  local reply=""
  printf '%b?%b %s %b[y/N]%b ' "$Y" "$N" "$1" "$DIM" "$N"
  read -r reply </dev/tty 2>/dev/null || reply=""   # empty (just Enter) = No
  [[ "$reply" =~ ^[Yy]$ ]]
}

# step "title" prints a divider + bold heading to visually separate each phase.
step() { hr; printf '%b%s%b\n' "$B" "$*" "$N"; }

# ============================================================================
#  MODEL REGISTRY
#  One line per model, fields separated by "|":
#     key       short name you type:  unsloth-serve <key>
#     repo      HuggingFace repo to download from
#     variant   the quant we use (quality/size tradeoff)
#     size      rough on-disk size (so you can budget)
#     hf-include  glob passed to `hf download --include` to pull ONLY that quant
#     note      one-line description
#  Kept as plain text (not an associative array) so it works on macOS's stock
#  bash 3.2. We parse it with `while IFS='|' read ...`.
# ============================================================================
# Ranked by the benchmark leaderboard. Start with ornith (#1). qwen stays the
# launcher's no-arg default (most-proven driver).
MODELS="\
ornith|tashfene/Ornith-1.0-35B-MTP-Q4_K_M-GGUF|Q4_K_M|~22 GB|*Q4_K_M*|#1 overall (bench 88.3) — no weak axis, MTP speculative decode
gemma|unsloth/gemma-4-26B-A4B-it-GGUF|UD-Q5_K_XL|~21 GB|*UD-Q5_K_XL*|#2 — fastest + cleanest tools (Gemma-4 MoE)
qwopus|Jackrong/Qwopus3.6-35B-A3B-Coder-MTP-GGUF|Q5_K_M|~25 GB|*Q5_K_M*|#3 — best pure coder (thinking-off coding lane)
opus|hesamation/Qwen3.6-35B-A3B-Claude-4.6-Opus-Reasoning-Distilled-GGUF|Q5_K_M|~23 GB|*Q5_K_M*|#4 — safest proven daily driver (Opus-4.6 distill, thinking-on)
glm|unsloth/GLM-4.7-Flash-GGUF|UD-Q5_K_XL|~22 GB|*UD-Q5_K_XL*|#5 — GLM-4.7-Flash (high quality, slower)
northmini|unsloth/North-Mini-Code-1.0-GGUF|UD-Q5_K_XL|~23 GB|*UD-Q5_K_XL*|#6 — Cohere North Mini, trained for OpenCode
qwen|unsloth/Qwen3.6-35B-A3B-MTP-GGUF|UD-Q5_K_S|~24 GB|*UD-Q5_K_S*|#7 — Qwen3.6-35B MTP (launcher default; best raw coding)
gpt-oss|ggml-org/gpt-oss-20b-GGUF|mxfp4|~12 GB|*mxfp4*|#9 — smallest/fastest, tiny-RAM pick (gpt-oss-20b)"

# Translate a repo id into its HuggingFace cache folder name.
# HF stores "org/Name" as "models--org--Name", so we just swap the "/" for "--".
#   unsloth/Qwen3.6-...-GGUF  ->  ~/.cache/huggingface/hub/models--unsloth--Qwen3.6-...-GGUF
hub_dir_for() { echo "$HUB/models--${1//\//--}"; }

# is a model already downloaded? ($1 repo, $2 include-glob)
# HF cache stores real files as hashed blobs; the variant-named entries under
# snapshots/ are SYMLINKS. We look for a snapshot entry whose NAME carries the
# variant tag AND whose blob is actually present (-e resolves the symlink, so a
# metadata-only / half-pulled repo correctly reads as NOT present).
model_present() {
  local d tag hit; d="$(hub_dir_for "$1")"
  [ -d "$d/snapshots" ] || return 1
  tag="$(echo "$2" | tr -d '*')"
  hit=$(find "$d/snapshots" -name "*$tag*.gguf" 2>/dev/null \
        | while read -r f; do [ -e "$f" ] && { echo yes; break; }; done)
  [ "$hit" = yes ]
}

# ============================================================================
say ""
say "${B}Unsloth Studio + OpenCode + Copilot — local coding stack installer${N}"
say "${DIM}mode: $([ "$AUTO" -eq 1 ] && echo 'AUTO (non-interactive)' || echo 'interactive'), system-tweaks: $([ "$WITH_SYSTEM" -eq 1 ] && echo on || echo 'opt-in')${N}"

# ---------------------------------------------------------------------------
step "0 · Preflight — detect environment & what's already installed"
# ---------------------------------------------------------------------------
[ "$(uname -s)" = "Darwin" ] || { err "This installer is macOS-only."; exit 1; }
if [ "$(uname -m)" = "arm64" ]; then ok "Apple Silicon ($(sysctl -n machdep.cpu.brand_string 2>/dev/null || echo arm64))"
else warn "Not arm64 — Metal GPU acceleration won't work; local models will be unusably slow."; fi

MEM_GB=$(( $(sysctl -n hw.memsize) / 1024 / 1024 / 1024 ))
if [ "$MEM_GB" -ge 32 ]; then ok "Unified memory: ${MEM_GB} GB"
elif [ "$MEM_GB" -ge 24 ]; then warn "Unified memory: ${MEM_GB} GB — the 35B driver is tight; prefer gpt-oss/glm."
else warn "Unified memory: ${MEM_GB} GB — below 24 GB, local agentic coding isn't really viable."; fi

FREE_GB=$(df -g "$HOME" | awk 'NR==2{print $4}')
ok "Free disk on \$HOME: ${FREE_GB} GB  ${DIM}(each model quant ≈ 12–24 GB)${N}"

say "  ${DIM}Detected tooling:${N}"
detect() { if command -v "$1" >/dev/null 2>&1; then printf '    %b✓%b %-14s %s\n' "$G" "$N" "$1" "$(eval "$2" 2>/dev/null | head -1)"; else printf '    %b·%b %-14s %s\n' "$DIM" "$N" "$1" "${DIM}not installed${N}"; fi; }
detect brew     "brew --version"
detect unsloth  "unsloth --version"
detect opencode "opencode --version"
detect copilot  "copilot --version"
detect hf       "echo present"
detect uv       "uv --version"

mkdir -p "$BIN_DIR" "$OC_DIR"

# ---------------------------------------------------------------------------
step "1 · Homebrew  ${DIM}(package manager — used only if you need node/uv)${N}"
# ---------------------------------------------------------------------------
if command -v brew >/dev/null 2>&1; then skip "Homebrew $(brew --version | head -1 | awk '{print $2}')"
else
  if ask "Install Homebrew? (official script, may prompt for your password)"; then
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    eval "$(/opt/homebrew/bin/brew shellenv 2>/dev/null || true)"
    ok "Homebrew installed"
  else warn "Skipped Homebrew — make sure you have node & uv some other way."; fi
fi

# ---------------------------------------------------------------------------
step "2 · Unsloth Studio  ${DIM}(patched llama.cpp engine + serving on :8888)${N}"
# ---------------------------------------------------------------------------
# Unsloth's own installer only reuses your system Node if it already meets its
# floor (node ^20.19||>=22.12||>=23 AND npm>=11) — otherwise it silently
# downloads its own "isolated" Node via Python's ssl module, which fails with
# a certificate error behind an SSL-inspecting corporate proxy (see
# UNSLOTH-CHEATSHEET.md). Bumping npm here makes it reuse the
# system Node instead, so that download never happens.
if command -v npm >/dev/null 2>&1; then
  NPM_VER="$(npm -v 2>/dev/null || true)"
  NPM_MAJOR="${NPM_VER%%.*}"
  case "$NPM_MAJOR" in ''|*[!0-9]*) NPM_MAJOR=0 ;; esac
  if [ "$NPM_MAJOR" -lt 11 ]; then
    if ask "npm is ${NPM_VER:-missing} — Unsloth Studio needs npm ≥11 to reuse it, otherwise it downloads its own Node (fails behind a corporate SSL-inspecting proxy). Upgrade npm now?  ${DIM}(npm install -g npm@latest)${N}"; then
      npm install -g npm@latest && ok "npm upgraded to $(npm -v)"
    else warn "Keeping npm $NPM_VER — Studio install may fail behind a corporate proxy (see UNSLOTH-CHEATSHEET.md)."; fi
  fi
else
  warn "No npm found — Unsloth Studio will download its own Node, which can fail behind a corporate SSL-inspecting proxy (see UNSLOTH-CHEATSHEET.md). Consider 'brew install node' first."
fi
# The llama.cpp engine itself is a SEPARATE download, hit by the identical SSL
# issue (GitHub release-manifest fetch via the same Python urllib path). If it
# fails, Unsloth falls back to building llama.cpp from source — but only if
# cmake is present; otherwise Studio installs in a "limited: llama.cpp
# unavailable" state with no llama-server binary at all, breaking every model,
# not just Studio-served ones (confirmed live behind a corporate proxy; see
# UNSLOTH-CHEATSHEET.md). git/make already ship with Xcode Command Line Tools.
if ! command -v cmake >/dev/null 2>&1; then
  if command -v brew >/dev/null 2>&1; then
    if ask "cmake not found — needed as a fallback to build llama.cpp from source if its prebuilt-binary download fails behind a corporate SSL-inspecting proxy. Install it now?  ${DIM}(brew install cmake)${N}"; then
      brew install cmake && ok "cmake installed"
    else warn "Skipping cmake — if the llama.cpp download fails behind a corporate proxy, Studio will have no engine to serve with (see UNSLOTH-CHEATSHEET.md)."; fi
  else
    warn "No cmake and no brew — if the llama.cpp download fails behind a corporate proxy, Studio will have no engine to serve with (see UNSLOTH-CHEATSHEET.md)."
  fi
fi
if command -v unsloth >/dev/null 2>&1; then
  skip "Unsloth Studio ($(unsloth --version 2>/dev/null | awk '{print $NF}'))"
  if ask "Re-run the installer to UPDATE Studio (pulls the current patched engine)?"; then
    curl -fsSL https://unsloth.ai/install.sh | sh && ok "Studio updated"
  fi
else
  if ask "Install Unsloth Studio?  ${DIM}(curl https://unsloth.ai/install.sh | sh — self-contained, nothing touches system Python)${N}"; then
    curl -fsSL https://unsloth.ai/install.sh | sh
    ok "Unsloth Studio installed → ~/.local/bin/unsloth"
  else warn "Skipped — the local models cannot run without it."; fi
fi

# ---------------------------------------------------------------------------
step "3 · OpenCode  ${DIM}(the agentic coding CLI, default model = local)${N}"
# ---------------------------------------------------------------------------
if command -v opencode >/dev/null 2>&1; then skip "OpenCode $(opencode --version 2>/dev/null)"
else
  if ask "Install OpenCode?  ${DIM}(curl https://opencode.ai/install | bash → ~/.opencode/bin)${N}"; then
    # The install script fetches a version manifest from GitHub first; behind a
    # corporate proxy that call fails with "Failed to fetch version information".
    # Homebrew doesn't hit that path, so fall back to it (a teammate confirmed brew
    # worked where the curl script didn't).
    if curl -fsSL https://opencode.ai/install | bash; then
      ok "OpenCode installed → ~/.opencode/bin/opencode"
    elif command -v brew >/dev/null 2>&1; then
      warn "opencode.ai install failed (often a corporate-proxy 'Failed to fetch version information') — falling back to Homebrew."
      if brew install opencode || brew install anomalyco/tap/opencode; then ok "OpenCode installed via Homebrew"
      else err "OpenCode install failed via both curl and brew — see https://opencode.ai/docs."; fi
    else
      err "OpenCode install failed and no Homebrew to fall back to. Install brew (step 1), then: brew install opencode"
    fi
  else warn "Skipped OpenCode."; fi
fi

# ---------------------------------------------------------------------------
step "4 · GitHub Copilot CLI  ${DIM}(@github/copilot — NOT the AWS 'copilot' brew formula)${N}"
# ---------------------------------------------------------------------------
if command -v copilot >/dev/null 2>&1 && copilot --version 2>/dev/null | grep -qi "GitHub Copilot"; then
  skip "$(copilot --version 2>/dev/null | head -1)"
else
  if command -v npm >/dev/null 2>&1; then
    if ask "Install GitHub Copilot CLI via  npm install -g @github/copilot ?"; then
      npm install -g @github/copilot && ok "Copilot CLI installed"
    else warn "Skipped Copilot CLI."; fi
  else warn "npm not found — install node first, then: npm install -g @github/copilot"; fi
fi

# ---------------------------------------------------------------------------
step "5 · Launcher  ${DIM}(~/bin/unsloth-serve — the 8-model serving script)${N}"
# ---------------------------------------------------------------------------
LAUNCHER="$BIN_DIR/unsloth-serve"
install_launcher=1
# `cmp -s A B` is a silent byte-for-byte compare (exit 0 = identical). So if the
# installed launcher already matches ours, there's literally nothing to do.
if [ -f "$LAUNCHER" ] && cmp -s "$ASSETS/unsloth-serve" "$LAUNCHER"; then
  # shellcheck disable=SC2088  # ~ is intentional display text here, not a path arg
  skip "~/bin/unsloth-serve (identical)"; install_launcher=0
fi
if [ "$install_launcher" -eq 1 ]; then
  if [ -f "$LAUNCHER" ]; then
    # shellcheck disable=SC2088  # ~ is intentional display text
    if ask "~/bin/unsloth-serve exists and differs — overwrite? (a .bak is kept)"; then
      cp "$LAUNCHER" "$LAUNCHER.bak.$$" && say "    ${DIM}backup → $LAUNCHER.bak.$$${N}"
    else install_launcher=0; warn "Kept your existing launcher."; fi
  else
    ask "Install ~/bin/unsloth-serve?" || install_launcher=0
  fi
  if [ "$install_launcher" -eq 1 ]; then
    cp "$ASSETS/unsloth-serve" "$LAUNCHER" && chmod +x "$LAUNCHER"
    ok "Installed ~/bin/unsloth-serve"
  fi
fi

# ---------------------------------------------------------------------------
step "6 · OpenCode config  ${DIM}(~/.config/opencode/opencode.json)${N}"
# ---------------------------------------------------------------------------
OCJSON="$OC_DIR/opencode.json"
if [ -f "$OCJSON" ] && cmp -s "$ASSETS/opencode.json" "$OCJSON"; then
  skip "opencode.json (identical)"
else
  do_cfg=1
  if [ -f "$OCJSON" ]; then
    if ask "opencode.json exists — replace with the team config? (a .bak is kept)"; then
      cp "$OCJSON" "$OCJSON.bak.$$" && say "    ${DIM}backup → $OCJSON.bak.$$${N}"
    else do_cfg=0; warn "Kept your existing opencode.json — merge the provider block manually (see INSTALL.md §6)."; fi
  else
    ask "Install the team opencode.json?" || do_cfg=0
  fi
  if [ "$do_cfg" -eq 1 ]; then cp "$ASSETS/opencode.json" "$OCJSON"; ok "Installed opencode.json"; fi
fi
say "    ${DIM}Plugins (dcp, quota) auto-install on first \`opencode\` run — nothing to do here.${N}"

# ---------------------------------------------------------------------------
step "7 · Shell environment  ${DIM}(PATH + UNSLOTH_STUDIO_API_KEY in ~/.zshenv)${N}"
# ---------------------------------------------------------------------------
# Idempotency: if our fenced block is already in ~/.zshenv, don't add it again.
if grep -qF "$MARK_BEGIN" "$ZSHENV" 2>/dev/null; then
  # shellcheck disable=SC2088  # ~ is intentional display text
  skip "~/.zshenv already has the setup block"
else
  if ask "Append PATH + UNSLOTH_STUDIO_API_KEY to ~/.zshenv?"; then
    # The localhost server doesn't verify a specific value, so any non-empty
    # "sk-unsloth-…" works — BUT prefer Studio's OWN minted key if it exists, so
    # the value is guaranteed correct even on a Studio build that does enforce it
    # (this was the #1 "missing/invalid API key" confusion in team testing). Field
    # name varies by version → try JSON, then any sk-… token, then a random key.
    KEY=""
    STUDIO_KEYFILE="$HOME/.unsloth/studio/auth/agent_api_key.json"
    if [ -f "$STUDIO_KEYFILE" ]; then
      KEY="$(python3 - "$STUDIO_KEYFILE" <<'PY' 2>/dev/null || true
import json,sys
try: d=json.load(open(sys.argv[1]))
except Exception: sys.exit(0)
if isinstance(d,dict):
    for k in ("api_key","apiKey","key","token","value"):
        v=d.get(k)
        if isinstance(v,str) and v.strip(): print(v.strip()); break
PY
)"
      [ -n "$KEY" ] || KEY="$(grep -oE 'sk-[A-Za-z0-9._-]+' "$STUDIO_KEYFILE" 2>/dev/null | head -1 || true)"
      [ -n "$KEY" ] && say "  ${DIM}Using Studio's minted localhost key from agent_api_key.json${N}"
    fi
    # `od` reads 6 random bytes as hex for a unique-ish throwaway if none was found.
    [ -n "$KEY" ] || KEY="sk-unsloth-local-$(od -An -N6 -tx1 /dev/urandom 2>/dev/null | tr -d ' \n' || echo team)"
    # Append our fenced block. The quoted 'EOF'-style heredoc via echo keeps the
    # $HOME/$PATH literal so it's expanded by YOUR shell at login, not right now.
    {
      echo ""
      echo "$MARK_BEGIN"
      # shellcheck disable=SC2016  # literal $HOME/$PATH ON PURPOSE — expanded at login, not now
      echo 'export PATH="$HOME/bin:$HOME/.local/bin:$HOME/.opencode/bin:$PATH"'
      echo "export UNSLOTH_STUDIO_API_KEY=\"$KEY\"   # localhost only — any non-empty value works"
      echo 'unsloth-key() { echo "$UNSLOTH_STUDIO_API_KEY"; }   # prints the localhost key OpenCode/Copilot use'
      # Your corporate CA bundle (if you are behind a TLS-inspecting proxy): tools that don't
      # use the macOS trust store must be pointed at the CA bundle explicitly, or model downloads
      # (Python/httpx) and Node MCP servers can't verify the intercepted chain. Guarded by
      # -f so it's a no-op — and never a FileNotFoundError — if you don't have the bundle.
      # shellcheck disable=SC2016  # literal $HOME ON PURPOSE — expanded at login, not now
      echo ''
      echo '# Your corporate CA bundle (if behind a TLS-inspecting proxy) — no-op if the bundle is absent'
      echo 'if [ -f "$HOME/.ssl/allCAbundle.pem" ]; then'
      echo '  export SSL_CERT_FILE="$HOME/.ssl/allCAbundle.pem"       # Python / httpx (hf downloads)'
      echo '  export REQUESTS_CA_BUNDLE="$HOME/.ssl/allCAbundle.pem"  # Python / requests-based tools'
      echo '  export NODE_EXTRA_CA_CERTS="$HOME/.ssl/allCAbundle.pem" # Node / npm MCP servers (context7 …)'
      echo 'fi'
      # `copilot` keeps its normal GitHub/enterprise auth by default.
      # `copilot-local [key]` is a BYOK wrapper (needs Copilot CLI 2026.04+) that points it at
      # the same local Unsloth endpoint OpenCode uses instead — a plain env var
      # (COPILOT_PROVIDER_BASE_URL) would silently disable GitHub auth for ALL copilot
      # calls, so we scope it to one function instead.
      # `key` just LABELS which model it's talking to (same keys as unsloth-serve) — it
      # does NOT switch models. Only one model is ever loaded on :8888 at a time, so `key`
      # must match whatever you last ran `unsloth-serve <key>` with. Getting the label right
      # matters for Copilot's own context/token-limit lookup, not for routing.
      echo 'copilot-local() {'
      echo '  local key="qwen"'
      echo '  case "${1:-}" in ornith|gemma|qwopus|opus|glm|northmini|qwen|gpt-oss) key="$1"; shift ;; esac'
      echo '  local model'
      echo '  case "$key" in'
      echo '    ornith)    model="tashfene/Ornith-1.0-35B-MTP-Q4_K_M-GGUF" ;;'
      echo '    gemma)     model="unsloth/gemma-4-26B-A4B-it-GGUF" ;;'
      echo '    qwopus)    model="Jackrong/Qwopus3.6-35B-A3B-Coder-MTP-GGUF" ;;'
      echo '    opus)      model="hesamation/Qwen3.6-35B-A3B-Claude-4.6-Opus-Reasoning-Distilled-GGUF" ;;'
      echo '    glm)       model="unsloth/GLM-4.7-Flash-GGUF" ;;'
      echo '    northmini) model="unsloth/North-Mini-Code-1.0-GGUF" ;;'
      echo '    qwen)      model="unsloth/Qwen3.6-35B-A3B-MTP-GGUF" ;;'
      echo '    gpt-oss)   model="gpt-oss-20b" ;;'
      echo '  esac'
      echo '  COPILOT_PROVIDER_BASE_URL="http://127.0.0.1:8888/v1" \'
      echo '  COPILOT_PROVIDER_API_KEY="$UNSLOTH_STUDIO_API_KEY" \'
      echo '  COPILOT_MODEL="$model" \'
      echo '  copilot "$@"'
      echo '}'
      echo '# export LITELLM_API_KEY="sk-..."       # optional: your LiteLLM gateway (put YOUR key)'
      echo '# export DEEPSEEK_API_KEY="sk-..."       # optional: DeepSeek fallback'
      echo "$MARK_END"
    } >> "$ZSHENV"
    ok "Wrote env block to ~/.zshenv  ${DIM}(open a new terminal to load it)${N}"
  else warn "Skipped — you must set UNSLOTH_STUDIO_API_KEY & PATH yourself (see INSTALL.md §7)."; fi
fi

# ---------------------------------------------------------------------------
step "8 · GPU wired-memory limit  ${DIM}(sudo — raises the Metal cap, persistent)${N}"
# ---------------------------------------------------------------------------
DAEMON=/Library/LaunchDaemons/local.unsloth.iogpu-wired-limit.plist
run_sys=0
# Always leave 4 GB of unified memory for macOS itself — scale the wired-limit
# to the machine actually detected in step 0, don't hardcode a 36 GB assumption.
WIRED_LIMIT_MB=$(( (MEM_GB - 4) * 1024 ))
if [ "$MEM_GB" -lt 32 ]; then
  warn "Skipped — needs ≥32 GB unified memory (this Mac has ${MEM_GB} GB); leaving the OS default in place."
elif [ "$AUTO" -eq 1 ] && [ "$WITH_SYSTEM" -eq 0 ]; then
  warn "Skipped in --auto (needs sudo). Re-run with --with-system, or do it manually (INSTALL.md §8)."
elif [ -f "$DAEMON" ]; then
  skip "GPU-limit daemon already installed  ${DIM}(current: $(sysctl -n iogpu.wired_limit_mb 2>/dev/null) MB)${N}"
else
  say "  ${DIM}This gives model weights + KV more room (${WIRED_LIMIT_MB} MB of ${MEM_GB} GB), leaving ~4 GB for macOS.${N}"
  ask "Install the GPU wired-limit LaunchDaemon? ${DIM}(will run: sudo — asks your password)${N}" && run_sys=1
fi
if [ "$run_sys" -eq 1 ]; then
  # The plist ships with __HOME__ and __WIRED_LIMIT_MB__ placeholders (plists
  # need literal values, not $HOME/$WIRED_LIMIT_MB); sed swaps both into a temp
  # copy first.
  TMP=$(mktemp); sed -e "s#__HOME__#$HOME#g" -e "s#__WIRED_LIMIT_MB__#$WIRED_LIMIT_MB#g" "$ASSETS/local.unsloth.iogpu-wired-limit.plist" > "$TMP"
  # Install it as a root-owned system daemon.
  sudo cp "$TMP" "$DAEMON" && sudo chown root:wheel "$DAEMON" && rm -f "$TMP"
  # Register it with launchd. `bootstrap` is the modern verb; `load -w` is the
  # older one — we try modern first and fall back so it works on any macOS.
  sudo launchctl bootstrap system "$DAEMON" 2>/dev/null || sudo launchctl load -w "$DAEMON" 2>/dev/null || true
  # Apply the limit right now too, so you don't have to reboot to benefit.
  sudo sysctl iogpu.wired_limit_mb="$WIRED_LIMIT_MB" >/dev/null
  ok "GPU wired limit → $(sysctl -n iogpu.wired_limit_mb) MB (persists across reboots)"
fi

# ---------------------------------------------------------------------------
step "9 · Login autostart  ${DIM}(LaunchAgent — boots the default model at login)${N}"
# ---------------------------------------------------------------------------
AGENT="$HOME/Library/LaunchAgents/com.user.unsloth-studio.plist"
run_agent=0
if [ "$AUTO" -eq 1 ] && [ "$WITH_SYSTEM" -eq 0 ]; then
  warn "Skipped in --auto. Re-run with --with-system, or install it manually (INSTALL.md §9)."
elif [ -f "$AGENT" ]; then
  skip "Autostart LaunchAgent already installed"
else
  ask "Autostart the default (qwen) model on login? ${DIM}(you can still Ctrl-C / switch models by hand)${N}" && run_agent=1
fi
if [ "$run_agent" -eq 1 ]; then
  mkdir -p "$HOME/Library/LaunchAgents"
  # Same __HOME__ → real-path substitution as the daemon above, but this is a
  # per-USER agent (no sudo). `gui/$(id -u)` targets your login GUI session.
  sed "s#__HOME__#$HOME#g" "$ASSETS/com.user.unsloth-studio.plist" > "$AGENT"
  launchctl bootstrap "gui/$(id -u)" "$AGENT" 2>/dev/null || launchctl load -w "$AGENT" 2>/dev/null || true
  ok "Installed autostart LaunchAgent"
fi

# ---------------------------------------------------------------------------
step "10 · Models  ${DIM}(pick which to download — this is the slow part)${N}"
# ---------------------------------------------------------------------------
if [ "$AUTO" -eq 1 ]; then
  warn "Skipped model download in --auto (too large to assume)."
  say  "  ${DIM}Download later with, e.g.:  hf download unsloth/Qwen3.6-35B-A3B-MTP-GGUF --include \"*UD-Q5_K_S*\""
  say  "  ${DIM}or just run  unsloth-serve ornith  — Studio auto-downloads on first launch.${N}"
else
  # Print a numbered menu of the fleet (leaderboard order), marking which are downloaded.
  # We build parallel arrays KEYS/REPOS/FILTERS indexed 0..n so the user's number
  # choice maps straight back to a model. (Parallel arrays, not a map, for bash 3.2.)
  say "  Available models (✓ = already on disk):"
  i=0; KEYS=(); REPOS=(); FILTERS=()
  while IFS='|' read -r k repo variant size filt note; do
    [ -n "$k" ] || continue
    i=$((i+1)); KEYS+=("$k"); REPOS+=("$repo"); FILTERS+=("$filt")
    if model_present "$repo" "$filt"; then mark="${G}✓${N}"; else mark=" "; fi   # tick if on disk
    printf '    [%d] %b %-9s %-7s %-8s %s\n' "$i" "$mark" "$k" "$variant" "$size" "$note"
  done <<< "$MODELS"
  say ""
  # Read the selection: space/comma list of numbers, or "all", or empty to skip.
  say "  ${DIM}Enter numbers to download (e.g. '1 5' or '1,5'), 'all', or leave empty to skip.${N}"
  printf '%b?%b models to download: ' "$Y" "$N"
  read -r picks </dev/tty 2>/dev/null || picks=""
  picks="${picks//,/ }"                       # turn commas into spaces so the loop can split
  [ "$picks" = "all" ] && picks="$(seq 1 "$i")"   # expand "all" to "1 2 3 …"

  if [ -n "$picks" ]; then
    # Make sure the `hf` downloader exists; prefer installing it via uv, else pip.
    if ! command -v hf >/dev/null 2>&1; then
      if ask "The 'hf' downloader isn't installed — install it via 'uv tool install huggingface_hub'?"; then
        if command -v uv >/dev/null 2>&1; then uv tool install "huggingface_hub[cli]"
        else python3 -m pip install --user "huggingface_hub[cli]"; fi
      fi
    fi
    # A HuggingFace login is what actually unblocked downloads for the team behind the
    # corporate VPN — anonymous requests get rate-limited / rejected through the TLS
    # proxy. Skips itself if you're already logged in. Reads the token from your keyboard.
    if command -v hf >/dev/null 2>&1; then
      if hf auth whoami >/dev/null 2>&1; then
        ok "HuggingFace: logged in as $(hf auth whoami 2>/dev/null | head -1)"
      elif ask "Log in to HuggingFace now? ${DIM}(free token → huggingface.co/settings/tokens — strongly recommended, especially on the VPN)${N}"; then
        hf auth login </dev/tty || warn "hf auth login didn't finish — re-run 'hf auth login' anytime."
      else
        warn "Not logged in to HuggingFace — downloads may fail on the VPN; run 'hf auth login' if they do."
      fi
    fi
    export HF_XET_HIGH_PERFORMANCE=1          # fast Xet-backend downloads (replaces the now-deprecated HF_HUB_ENABLE_HF_TRANSFER)
    # Corporate TLS-inspection (if you are behind such a proxy) makes hf's Python/httpx
    # download fail with "certificate verify failed: self-signed certificate in
    # certificate chain" — Python ignores the macOS trust store. If a corporate CA
    # bundle is present and SSL_CERT_FILE isn't already set, point Python at it so the
    # intercepted chain verifies. Guarded by -f so it can NEVER point at a missing file
    # (which would make every Python/httpx tool throw FileNotFoundError, not just this).
    CA_BUNDLE="$HOME/.ssl/allCAbundle.pem"
    if [ -z "${SSL_CERT_FILE:-}" ] && [ -f "$CA_BUNDLE" ]; then
      export SSL_CERT_FILE="$CA_BUNDLE"
      export REQUESTS_CA_BUNDLE="$CA_BUNDLE"
      say "  ${DIM}Corporate CA bundle detected — using it for downloads: $CA_BUNDLE${N}"
    fi
    # Loop over each chosen number, map it back to a model, and download it. Count
    # outcomes so we can fail LOUD at the end instead of printing a cheery "done".
    dl_ok=0; dl_fail=0; dl_failed=""
    for n in $picks; do
      # Reject anything that isn't a plain number BEFORE doing arithmetic —
      # otherwise a typo like "y" or "1a" would crash the script under `set -u`.
      case "$n" in ''|*[!0-9]*) warn "ignoring '$n' (not a number)"; continue ;; esac
      idx=$((n-1))                            # menu is 1-based, arrays are 0-based
      # Guard against out-of-range numbers (e.g. "9" when there are only 5).
      [ "$idx" -ge 0 ] && [ "$idx" -lt "${#KEYS[@]}" ] || { warn "ignoring '$n' (out of range)"; continue; }
      repo="${REPOS[$idx]}"; filt="${FILTERS[$idx]}"
      # Skip anything already on disk (idempotent — safe to re-run).
      if model_present "$repo" "$filt"; then skip "${KEYS[$idx]} ($repo)"; continue; fi
      say "  ${C}↓${N} downloading ${KEYS[$idx]}: $repo  (include $filt)"
      # --include pulls ONLY the one quant we want, not the whole multi-quant repo.
      if hf download "$repo" --include "$filt"; then
        dl_ok=$((dl_ok+1))
      else
        dl_fail=$((dl_fail+1)); dl_failed="$dl_failed ${KEYS[$idx]}"
        warn "download of $repo failed — retry later"
      fi
    done
    # Fail LOUD on a total wipe-out — a "✓ done" printed over five failed downloads
    # is the #1 way people end up with a broken setup and no idea why. Corporate SSL
    # inspection is the usual culprit (see the CA note above), so point at the fix.
    if [ "$dl_fail" -gt 0 ] && [ "$dl_ok" -eq 0 ]; then
      err "All ${dl_fail} model download(s) failed —${dl_failed}."
      say "  ${Y}On a corporate VPN this is almost always TLS inspection: hf (Python) can't verify the chain.${N}"
      if [ -n "${SSL_CERT_FILE:-}" ]; then
        say "  ${DIM}SSL_CERT_FILE is set ($SSL_CERT_FILE) but downloads still failed — check it's the right corporate CA bundle and the VPN is connected.${N}"
      else
        say "  ${DIM}Fix: point Python at your corporate CA bundle, then re-run ./install.sh:${N}"
        say "    export SSL_CERT_FILE=\"\$HOME/.ssl/allCAbundle.pem\""
        say "    export REQUESTS_CA_BUNDLE=\"\$HOME/.ssl/allCAbundle.pem\""
        say "  ${DIM}No bundle there? Get your corporate CA from IT, or build one from your keychain:${N}"
        say "    security find-certificate -a -p /Library/Keychains/System.keychain > ~/.ssl/allCAbundle.pem"
      fi
      exit 1
    elif [ "$dl_fail" -gt 0 ]; then
      warn "${dl_ok} model(s) downloaded, ${dl_fail} failed:${dl_failed} — re-run ./install.sh for those."
    else
      ok "Model downloads done — ${dl_ok} downloaded"
    fi
  else
    warn "No models selected — download later or let Studio auto-fetch on first serve."
  fi
fi

# ---------------------------------------------------------------------------
step "✔ Done — verify"
# ---------------------------------------------------------------------------
say "  ${DIM}Open a NEW terminal (to load ~/.zshenv), then:${N}"
say "    unsloth-serve ornith               ${DIM}# start the benchmark #1 model on :8888${N}"
say "    # then use it from VS Code (Copilot Chat → BYOK, see INSTALL.md §12),"
say "    # or from the CLI:  opencode        ${DIM}# talks to the local model by default${N}"
say ""
say "  ${DIM}Quick endpoint check once a model is serving:${N}"
say "    curl -s http://127.0.0.1:8888/v1/models -H \"Authorization: Bearer \$UNSLOTH_STUDIO_API_KEY\" | python3 -m json.tool"
say ""
say "  ${B}If OpenCode / VS Code Copilot says \"Invalid or expired API key\"${N} it almost never means the key:"
say "    1) is a model serving?  ${C}unsloth-serve ornith${N}   ${DIM}(wait for \"model loaded\")${N}"
say "    2) new terminal (or ${C}source ~/.zshenv${N}) so UNSLOTH_STUDIO_API_KEY is set   ${DIM}(check with: unsloth-key)${N}"
say ""
say "  ${B}Cheat-sheet:${N} UNSLOTH-CHEATSHEET.md   ${B}Full manual:${N} INSTALL.md"
hr
