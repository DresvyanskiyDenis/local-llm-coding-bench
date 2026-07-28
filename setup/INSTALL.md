# Local-LLM coding stack — full manual installation

Set up a **fully local, private coding agent** on your Mac: [Unsloth Studio](https://unsloth.ai)
serves an open-weight model on `localhost:8888`, and [OpenCode](https://opencode.ai) (plus GitHub
Copilot CLI) talks to it. No per-token cost, no code leaving your machine. This is Denis's
day-to-day setup, cleaned of personal infrastructure.

> **Prefer the script?** `./install.sh` does all of this interactively (asks before every step) or
> `./install.sh --auto` does it unattended (except model downloads and the sudo/login tweaks). This
> file is the **manual** path — for when you'd rather run each command yourself and see exactly what
> it does. Both paths install the identical files from `assets/`.

Every step here starts with a **"check first"** so you never reinstall something you already have.

---

## 0. Prerequisites & what you're installing

| Requirement | Check | Notes |
|---|---|---|
| **Apple Silicon Mac** (M1–M4) | `uname -m` → `arm64` | Intel Macs get no Metal GPU accel — don't bother. |
| **Unified memory** | `echo $(( $(sysctl -n hw.memsize)/1024/1024/1024 )) GB` | 36 GB = comfortable for the 35B driver. 24 GB → use `gpt-oss`/`glm`. <24 GB → not viable. |
| **Free disk** | `df -g ~ \| awk 'NR==2{print $4" GB"}'` | ~12–24 GB **per model**. |
| **node + npm** | `command -v npm` | Needed for OpenCode plugins & Copilot CLI. Comes with most dev setups / Homebrew. |

The stack, end to end:

```
  ┌ unsloth-serve (launcher, ~/bin) ──► Unsloth Studio ──► patched llama.cpp ──► :8888  (OpenAI-compatible)
  │                                                                                  ▲
  └ models in ~/.cache/huggingface/hub                          VS Code Copilot Chat │  (BYOK — the PRIMARY client, §12)
                                                                       OpenCode ─────┤  (optional CLI; default model = local)
                                                                       Copilot CLI ──┘  (optional; copilot-local BYOK wrapper)
```

> **Which client?** For most people the primary way to use the local model is **VS Code — GitHub
> Copilot Chat's Custom Endpoint (BYOK)** (§12). The steps below install the whole serving stack;
> the **OpenCode** CLI (§3, §6) is **optional** — only needed if you also want the terminal agent.

---

## 1. Homebrew *(only if you don't have node/uv another way)*

**Check first:**
```bash
command -v brew && brew --version
```
If missing and you want it:
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```
Then follow its "Next steps" to add `brew` to your `PATH`.

---

## 2. Unsloth Studio — the serving engine

This is the **one non-negotiable piece**: the daily-driver model is an **MTP** ("Multi-Token
Prediction") GGUF, and the MTP format only loads/accelerates on Unsloth Studio's **patched**
`llama.cpp` (it reports *"Compiled by the Unsloth team"*). Stock llama.cpp / LM Studio either fail
to load it or show no speedup.

**Coming from LM Studio + MLX?** This setup deliberately uses GGUF instead. In testing, several
models that looked "broken" on MLX turned out to be runtime bugs, not bad weights — the identical
weights ran clean on GGUF (one case, GLM-4.7-Flash's KV-cache handling, even triggered a macOS
kernel panic on MLX). MLX still wins on raw decode speed for single-model chat; GGUF/llama.cpp was
the more mature, reliable choice here specifically for agentic work (long contexts, tool-calling).
See README.md → "Why GGUF, not MLX?" for the full breakdown. Wondering about Ollama instead? See
README.md → "Why Unsloth Studio, not Ollama?" — short version: MTP speculative decoding, better
quant quality, and fresher model drops, traded against Ollama's simpler out-of-the-box tool
integration.

**Check first:**
```bash
command -v unsloth && unsloth --version      # e.g. 2026.6.9
```
**Behind a corporate VPN?** Unsloth's installer downloads Node + a prebuilt `llama.cpp` binary via
Python, which can fail with `SSL: CERTIFICATE_VERIFY_FAILED … Missing Authority Key Identifier`
behind GlobalProtect. This isn't anything wrong with your Mac or a sign of a MITM/security issue —
it's two ordinary things stacking: GlobalProtect's standard SSL inspection (the same feature that
protects you on any corporate network) plus Python 3.13 shipping stricter certificate checks than
older Python did. curl, Homebrew, and npm are all unaffected — only these two Python-driven
downloads inside Unsloth's installer trip on it. Nothing to report to IT, nothing to disable.

The fix is two prerequisites that make Unsloth skip those downloads entirely (Node gets reused
from your system install, llama.cpp gets built locally from source instead) — worth having
*before* you run the one-liner below:
```bash
npm -v            # need ≥11 — if lower: npm install -g npm@latest
command -v cmake  # if missing: brew install cmake (enables a local source-build fallback)
```
`install.sh` checks and offers to fix both automatically if you use the automated path instead —
you don't need to think about this at all unless you're running Unsloth's installer by hand. The
only visible effect is the install taking ~20–25 minutes instead of a couple, while llama.cpp
compiles from source. See `UNSLOTH-CHEATSHEET.md` → "When something's wrong" for the full story.

Install (the **same one-liner updates it** later — keep it current for the patched engine):
```bash
curl -fsSL https://unsloth.ai/install.sh | sh
```
This drops a **self-contained bundle** in `~/.unsloth/` (its own Python venv, bundled `llama.cpp`, a
small web UI) and a launcher at `~/.local/bin/unsloth`. Nothing touches system Python. Make sure
`~/.local/bin` is on your `PATH` (step 7). If the SSL issue above hits and you don't have `cmake`
yet, Studio will still finish "installed" but the engine will be missing — install `cmake` and
re-run the one-liner.

Verify the patched engine:
```bash
~/.unsloth/llama.cpp/llama-server --version   # should say "Compiled by the Unsloth team"
```
(If the SSL issue above forced a local source build, this binary lives at
`~/.unsloth/llama.cpp/build/bin/llama-server` instead and its `--version` won't say "Compiled by
the Unsloth team" — that's expected, it's still the same patched source, just built locally instead
of downloaded prebuilt.)

---

## 3. OpenCode — the coding agent *(optional — CLI users only; VS Code Copilot users can skip to §5)*

**Check first:**
```bash
command -v opencode && opencode --version     # e.g. 1.17.18
```
Install:
```bash
curl -fsSL https://opencode.ai/install | bash    # → ~/.opencode/bin/opencode
```
> **`Failed to fetch version information`?** The install script fetches a version manifest from
> GitHub first, which a corporate proxy can block. Homebrew doesn't hit that path — use it instead:
> `brew install opencode` (or the fresher `brew install anomalyco/tap/opencode`). `install.sh` does
> this fallback automatically.

---

## 4. GitHub Copilot CLI

> ⚠️ **Not** `brew install copilot` — that's the *AWS* Copilot (ECS/Fargate), a different tool.
> GitHub Copilot CLI ships as an **npm package**.

**Check first:**
```bash
copilot --version 2>/dev/null | grep -qi "GitHub Copilot" && echo "already installed"
```
Install:
```bash
npm install -g @github/copilot        # symlinks a `copilot` binary into your npm global bin
```
Authenticate on first run: `copilot` → `/login` (uses your GitHub / enterprise account).

---

## 5. The launcher — `~/bin/unsloth-serve`

Codifies the serving flags for all 8 fleet models so you never retype them (leaderboard order:
`ornith` `gemma` `qwopus` `opus` `glm` `northmini` `qwen` `gpt-oss`; `qwen` is the no-arg default).
One model at a time (36 GB holds exactly one). Note `unsloth-serve` is **our** script (it ships in
this bundle's `assets/`) — it is *not* part of Unsloth Studio, so don't go looking for it under
`~/.unsloth`.

**Check first:** `ls -l ~/bin/unsloth-serve`. Install:
```bash
mkdir -p ~/bin
cp assets/unsloth-serve ~/bin/unsloth-serve
chmod +x ~/bin/unsloth-serve
```

Usage (each serves on `:8888`; stop the running one with **Ctrl-C** before switching):
```bash
unsloth-serve            # qwen — the no-arg default
unsloth-serve ornith     # #1 overall — no weak axis
unsloth-serve gemma      # #2 — fastest + cleanest tools
unsloth-serve qwopus     # #3 — best pure coder
unsloth-serve opus       # #4 — Opus-4.6 reasoning distill
unsloth-serve glm        # #5 — 2nd coding driver (slower, high quality)
unsloth-serve northmini  # #6 — agentic, OpenCode-trained
unsloth-serve qwen       # #7 — same as the bare command above
unsloth-serve gpt-oss    # #9 — smallest/fastest (~12 GB)
```

> **Why `-c 131072`, not the model's full native context (some go to 256K)?** The KV-cache for a
> 256K window won't fit next to the weights in 36 GB — it spills to swap and everything crawls. 128K
> served / 90K used (the `opencode.json` cap, §6) is the sweet spot on 36 GB; raise `-c` only if you
> have RAM headroom to spare.

The launcher also streams an **inline prefill progress bar** into the same terminal for the
Studio-served models (`qwen`/`opus`/`glm`/`gemma`) — the LM-Studio-style `progress = 0.XX` line that
Studio otherwise hides in a logfile. Appears only for prefills ≥3 s (same as LM Studio); `gpt-oss`,
`northmini`, `ornith` and `qwopus` are direct-served and print it natively. See
**UNSLOTH-CHEATSHEET.md** for the per-flag rationale.

---

## 6. OpenCode configuration *(optional — only if you installed OpenCode in §3)*

**Check first:** `ls ~/.config/opencode/opencode.json` (back it up if it exists — you may already
have your own).

```bash
mkdir -p ~/.config/opencode
# back up any existing config, then install the team one:
[ -f ~/.config/opencode/opencode.json ] && cp ~/.config/opencode/opencode.json ~/.config/opencode/opencode.json.bak
cp assets/opencode.json ~/.config/opencode/opencode.json
```

What this config gives you (already cleaned of Denis's personal infra — no home-server MCP, no
vault plugins, no personal keys):

- **Default model = local** `unsloth-studio/unsloth/Qwen3.6-35B-A3B-MTP-GGUF`, with all 5 local
  models registered.
- **`compaction` + per-model `limit.context: 90000`** — the important safety net. Studio launches
  every model with `--no-context-shift`; when a session outgrows the server's real context,
  llama-server returns a hard error instead of shifting, and OpenCode (a plain OpenAI client) then
  **hangs with the GPU at 0 %**. The `limit.context: 90000` makes OpenCode auto-compact *before* it
  ever hits that wall. **Keep this** unless you serve a model at a smaller `-c`.
- **Cloud fallbacks (optional, you add your own keys):** LiteLLM (your LiteLLM gateway, e.g.
  `your-litellm-gateway.example.com` — user-supplied), GitHub Copilot enterprise (your enterprise
  GitHub, e.g. `your-enterprise-github.example.com` — user-supplied), DeepSeek. Cloud Anthropic/Google
  are disabled by design (local-first).
- **`context7` MCP enabled** (official-docs lookups). Others (`playwright`, `firecrawl`,
  `atlassian`) are present but `enabled: false` — turn on per-need and supply their env keys.
- **A hardened `permission` block** — read-only git & common tools auto-allowed; destructive
  commands (`rm -rf`, `sudo`, force-push, `mkfs`, `curl|bash`, …) hard-denied; secret files
  (`.env`, keys, `*.pem`) blocked from read/write.

Plugins (`@tarquinen/opencode-dcp`, `@slkiser/opencode-quota`) are pinned in the config and
**auto-install on your first `opencode` run** — nothing to do by hand.

---

## 7. Shell environment (`~/.zshenv`)

OpenCode reads the local-server API key and finds the binaries from your shell env.

**Check first:** `grep unsloth+opencode ~/.zshenv`. Append:
```bash
cat >> ~/.zshenv <<'EOF'

# >>> unsloth+opencode team setup >>>
export PATH="$HOME/bin:$HOME/.local/bin:$HOME/.opencode/bin:$PATH"
export UNSLOTH_STUDIO_API_KEY="sk-unsloth-local-CHANGEME"   # localhost only — any non-empty value works
unsloth-key() { echo "$UNSLOTH_STUDIO_API_KEY"; }          # prints the key OpenCode/Copilot use
# Corporate TLS-inspection CA (if you're behind a TLS-intercepting proxy) — no-op if the bundle is absent. Lets
# hf model downloads (Python) and Node MCP servers verify the intercepted chain; see the note below + §10.
if [ -f "$HOME/.ssl/allCAbundle.pem" ]; then
  export SSL_CERT_FILE="$HOME/.ssl/allCAbundle.pem"       # Python / httpx (hf downloads)
  export REQUESTS_CA_BUNDLE="$HOME/.ssl/allCAbundle.pem"  # Python / requests-based tools
  export NODE_EXTRA_CA_CERTS="$HOME/.ssl/allCAbundle.pem" # Node / npm MCP servers (context7 …)
fi
copilot-local() {
  local key="qwen"
  case "${1:-}" in ornith|gemma|qwopus|opus|glm|northmini|qwen|gpt-oss) key="$1"; shift ;; esac
  local model
  case "$key" in
    ornith)    model="tashfene/Ornith-1.0-35B-MTP-Q4_K_M-GGUF" ;;
    gemma)     model="unsloth/gemma-4-26B-A4B-it-GGUF" ;;
    qwopus)    model="Jackrong/Qwopus3.6-35B-A3B-Coder-MTP-GGUF" ;;
    opus)      model="hesamation/Qwen3.6-35B-A3B-Claude-4.6-Opus-Reasoning-Distilled-GGUF" ;;
    glm)       model="unsloth/GLM-4.7-Flash-GGUF" ;;
    northmini) model="unsloth/North-Mini-Code-1.0-GGUF" ;;
    qwen)      model="unsloth/Qwen3.6-35B-A3B-MTP-GGUF" ;;
    gpt-oss)   model="gpt-oss-20b" ;;
  esac
  COPILOT_PROVIDER_BASE_URL="http://127.0.0.1:8888/v1" \
  COPILOT_PROVIDER_API_KEY="$UNSLOTH_STUDIO_API_KEY" \
  COPILOT_MODEL="$model" \
  copilot "$@"
}
# export LITELLM_API_KEY="sk-..."        # optional: your LiteLLM gateway (YOUR key)
# export DEEPSEEK_API_KEY="sk-..."        # optional: DeepSeek fallback
# <<< unsloth+opencode team setup <<<
EOF
```
Then **open a new terminal** (or `source ~/.zshenv`).

> **Copilot CLI + the local model:** plain `copilot` keeps its normal GitHub/enterprise
> (e.g. `your-enterprise-github.example.com` — user-supplied) auth and cloud models — untouched. `copilot-local [key]` is a BYOK
> (Bring-Your-Own-Key) wrapper (needs Copilot CLI **2026.04+**; check with `copilot --version`)
> that points that one invocation at the local Unsloth endpoint OpenCode uses, no GitHub auth
> needed. We scope it to a function instead of exporting `COPILOT_PROVIDER_BASE_URL` globally,
> because that env var **disables GitHub auth for every `copilot` call** the moment it's set —
> that would silently break normal cloud/enterprise Copilot for the whole shell.
>
> **`key` (`ornith`/`gemma`/`qwopus`/`opus`/`glm`/`northmini`/`qwen`/`gpt-oss`, default `qwen`)
> only LABELS which model you're talking to — it does not switch models.** Only one local model is
> ever loaded on `:8888` at a time (same 36 GB constraint as everything else here), so `key` must
> match whatever you last ran `unsloth-serve <key>` with — see §5. Getting the label right matters
> for Copilot's own context/token-limit lookup; the actual reply always comes from whichever
> model is loaded, regardless of what's requested (Studio doesn't validate the `model` field).

> **About `UNSLOTH_STUDIO_API_KEY` — and the "Invalid or expired API key" error:** that OpenCode
> error almost never means the key is wrong. It means either **(a)** no model is serving on `:8888`
> yet — run `unsloth-serve ornith` and wait for "model loaded" — or **(b)** the variable isn't set in
> *this* shell: open a **new terminal** (or `source ~/.zshenv`) and check with `unsloth-key`. The
> endpoint is on `127.0.0.1` only and doesn't enforce a specific value, so **any non-empty
> `sk-unsloth-…` string works**. `install.sh` prefers Studio's own minted key
> (`~/.unsloth/studio/auth/agent_api_key.json`) when present, so it stays correct even if a future
> Studio build starts enforcing it — but you never need to match it by hand for localhost.
>
> **Corporate cert note:** the guarded `if [ -f "$HOME/.ssl/allCAbundle.pem" ]` block in the heredoc
> above is what handles a corporate TLS-inspecting proxy (if you're behind one). Tools that don't
> use macOS's system trust store must be pointed at your corporate CA bundle explicitly — **Node** reads
> `NODE_EXTRA_CA_CERTS` (used by the `context7` MCP and other npm tools), **Python/httpx** reads
> `SSL_CERT_FILE` / `REQUESTS_CA_BUNDLE` (used by `hf download` — this is what makes model downloads
> fail otherwise, see §10). All three are exported together, guarded so they no-op if the bundle is
> absent. No bundle? Point them at your own CA bundle, or set `"enabled": false` on `context7` in
> `opencode.json` (that only handles the Node half — Python downloads still need §10's fix).

---

## 8. GPU wired-memory limit *(optional, needs `sudo`, ≥32 GB machines only)*

Apple Silicon caps how much unified memory the GPU may "wire" for weights + KV
(`iogpu.wired_limit_mb`, default ≈ 75 % of RAM). Raising it gives the model more room while
**always leaving 4 GB for macOS + OpenCode** — the limit is `(your RAM in GB − 4) × 1024`, not a
flat number, so it scales to the machine you're actually on (28672 on 32 GB, 32768 on 36 GB, etc).
Below 32 GB, skip this step — there's not enough headroom to raise the cap safely.

**Check first:** `sysctl iogpu.wired_limit_mb` (0 or ~75 % of RAM = default).

Apply now + make it persist across reboots (root LaunchDaemon):
```bash
WIRED_LIMIT_MB=$(( $(( $(sysctl -n hw.memsize)/1024/1024/1024 )) * 1024 - 4096 ))
sudo sed -e "s#__HOME__#$HOME#g" -e "s#__WIRED_LIMIT_MB__#$WIRED_LIMIT_MB#g" assets/local.unsloth.iogpu-wired-limit.plist \
  | sudo tee /Library/LaunchDaemons/local.unsloth.iogpu-wired-limit.plist >/dev/null
sudo chown root:wheel /Library/LaunchDaemons/local.unsloth.iogpu-wired-limit.plist
sudo launchctl bootstrap system /Library/LaunchDaemons/local.unsloth.iogpu-wired-limit.plist
sudo sysctl iogpu.wired_limit_mb="$WIRED_LIMIT_MB"    # apply immediately, no reboot
sysctl iogpu.wired_limit_mb                            # verify → matches $WIRED_LIMIT_MB
```

> ⚠️ **Do not hand-edit the limit closer to your total RAM** — starving the OS triggers the exact
> swap-death / GPU-stall this is meant to prevent. A running server sizes its KV at launch, so
> restart the model after raising the cap to actually use the headroom.

To undo: `sudo launchctl bootout system /Library/LaunchDaemons/local.unsloth.iogpu-wired-limit.plist && sudo rm /Library/LaunchDaemons/local.unsloth.iogpu-wired-limit.plist`.

---

## 9. Login autostart *(optional)*

Boot the default (`qwen`) model at login so `:8888` is always warm.

**Check first:** `ls ~/Library/LaunchAgents/com.user.unsloth-studio.plist`. Install:
```bash
mkdir -p ~/Library/LaunchAgents
sed "s#__HOME__#$HOME#g" assets/com.user.unsloth-studio.plist \
  > ~/Library/LaunchAgents/com.user.unsloth-studio.plist
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.user.unsloth-studio.plist
```
`RunAtLoad=true, KeepAlive=false` → starts at login, does **not** respawn if you Ctrl-C it (so you
can freely switch models). To undo: `launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/com.user.unsloth-studio.plist && rm ~/Library/LaunchAgents/com.user.unsloth-studio.plist`.

---

## 10. Download models

Files land in `~/.cache/huggingface/hub` — exactly where Studio's `--model` looks. The `--include`
glob pulls **only** that one quant (repos hold many).

**Check first** (already downloaded?):
```bash
ls -d ~/.cache/huggingface/hub/models--unsloth--Qwen3.6-35B-A3B-MTP-GGUF 2>/dev/null && echo "qwen repo present"
```

Get the `hf` downloader if needed, **log in**, and enable fast transfer:
```bash
uv tool install "huggingface_hub[cli]"   # no uv? python3 -m pip install --user "huggingface_hub[cli]"
hf auth login                            # paste a free token from huggingface.co/settings/tokens
export HF_XET_HIGH_PERFORMANCE=1         # fast Xet-backend downloads
```
`install.sh` does these same steps, but note its prompt overstates what it runs: it offers to
"install it via `uv tool install huggingface_hub`" and then falls back to
`python3 -m pip install --user` whenever `uv` isn't on the machine — it detects `uv`, it never
installs it. On a fresh corporate Mac that pip fallback is usually the path you actually get.

> **`hf auth login` matters most on the VPN.** Anonymous downloads get rate-limited / rejected
> through the corporate TLS proxy; logging in with a (free) HuggingFace token is what unblocked
> downloads for the team — try it *before* blaming the CA/cert setup below. (The old
> `export HF_HUB_ENABLE_HF_TRANSFER=1` from earlier guides is now a deprecated no-op — the Hub moved
> to the Xet backend; `HF_XET_HIGH_PERFORMANCE=1` is the modern equivalent.)

Pick what you need (you don't need all 8 — start with `ornith`):

| Model | Size | Command |
|---|---|---|
| **ornith** (#1 overall) | ~22 GB | `hf download tashfene/Ornith-1.0-35B-MTP-Q4_K_M-GGUF --include "*Q4_K_M*"` |
| **gemma** (#2 fastest) | ~21 GB | `hf download unsloth/gemma-4-26B-A4B-it-GGUF --include "*UD-Q5_K_XL*"` |
| **qwopus** (#3 best coder) | ~25 GB | `hf download Jackrong/Qwopus3.6-35B-A3B-Coder-MTP-GGUF --include "*Q5_K_M*"` |
| **opus** (#4 distill) | ~23 GB | `hf download hesamation/Qwen3.6-35B-A3B-Claude-4.6-Opus-Reasoning-Distilled-GGUF --include "*Q5_K_M*"` |
| **glm** (#5 2nd driver) | ~22 GB | `hf download unsloth/GLM-4.7-Flash-GGUF --include "*UD-Q5_K_XL*"` |
| **northmini** (#6 agentic) | ~23 GB | `hf download unsloth/North-Mini-Code-1.0-GGUF --include "*UD-Q5_K_XL*"` |
| **qwen** (#7 launcher default) | ~24 GB | `hf download unsloth/Qwen3.6-35B-A3B-MTP-GGUF --include "*UD-Q5_K_S*"` |
| **gpt-oss** (#9 tiny-RAM) | ~12 GB | `hf download ggml-org/gpt-oss-20b-GGUF --include "*mxfp4*"` |

> **Behind a corporate VPN? `certificate verify failed` on HuggingFace downloads.** `hf download`
> (Python/httpx) fails with `[SSL: CERTIFICATE_VERIFY_FAILED] … self-signed certificate in
> certificate chain`. This is the same GlobalProtect SSL-inspection issue as §2 (step 1). The script
> will retry and may eventually succeed, but if it doesn't, you have two options:
>
> **Option 1 (CA bundle, permanent):** Point Python at your corporate CA bundle (if you're behind a
> TLS-intercepting proxy) — the same
> `~/.ssl/allCAbundle.pem` Node uses via `NODE_EXTRA_CA_CERTS` (§7):
> ```bash
> export SSL_CERT_FILE="$HOME/.ssl/allCAbundle.pem"
> export REQUESTS_CA_BUNDLE="$HOME/.ssl/allCAbundle.pem"
> ```
> Re-run the download (or `install.sh`) in that same shell. To make it permanent, add those two
> lines to `~/.zshenv` and open a new terminal. **The path must point to a file that exists** — if
> `SSL_CERT_FILE` names a missing file, *every* Python/httpx tool aborts immediately with
> `FileNotFoundError: … No such file or directory` (not just downloads). No bundle at
> `~/.ssl/allCAbundle.pem`? Get it from IT or build one from your keychain:
> `security find-certificate -a -p /Library/Keychains/System.keychain > ~/.ssl/allCAbundle.pem`.
>
> **Option 2 (defer, simpler):** Skip downloading in step 10. Unsloth auto-downloads missing models
> on their first `unsloth-serve <key>` launch; you just wait a minute during startup instead. The
> auto-download uses the same Python path, so the CA fix (Option 1) applies there too if needed.
> Models that fail to download in step 10 are noted — you can always retry them later with
> `unsloth-serve <key>`.

---

## 11. Verify it all works

Open a **new terminal** (so `~/.zshenv` is loaded), then:

```bash
unsloth-serve ornith      # starts the benchmark #1 model; wait for "model loaded" / listening on :8888
```
In another terminal:
```bash
# raw endpoint check
curl -s http://127.0.0.1:8888/v1/models \
  -H "Authorization: Bearer $UNSLOTH_STUDIO_API_KEY" | python3 -m json.tool

# real tool-calling check (a 3-word reply)
curl -s http://127.0.0.1:8888/v1/chat/completions \
  -H "Authorization: Bearer $UNSLOTH_STUDIO_API_KEY" -H "Content-Type: application/json" \
  -d '{"model":"unsloth/Qwen3.6-35B-A3B-MTP-GGUF","messages":[{"role":"user","content":"say hi in 3 words"}]}' \
  | python3 -m json.tool
```
Then just run `opencode` in any project — it talks to the local model by default. Switch models
inside OpenCode with `/models`, or point `unsloth-serve` at a different one.

> **Getting "Invalid or expired API key" in OpenCode?** It's not a bad key — a model just isn't
> serving on `:8888` yet (`unsloth-serve ornith`, wait for "model loaded"), or the env var isn't
> loaded in this shell (new terminal / `source ~/.zshenv`; verify with `unsloth-key`). See §7.

Copilot CLI on the same local model (BYOK — needs Copilot CLI 2026.04+):
```bash
copilot-local -p "say hi in 3 words" --allow-all-tools -s        # talks to whatever's on :8888
copilot-local glm -p "say hi in 3 words" --allow-all-tools -s    # only correct if you ran
                                                                   # `unsloth-serve glm` first
```
Plain `copilot` (no `-local`) still uses your normal GitHub/enterprise auth and cloud models.

**Expected on an M4 Max / 36 GB:** ~85 tok/s short prompts, 34–50 tok/s in long agentic sessions;
prefill (prompt processing) ~200–400 tok/s is the real latency driver.

---

## 12. VS Code Copilot Chat — local model via BYOK *(the primary client for most people)*

Point VS Code's Copilot Chat extension (chat panel, inline chat, **and Agent mode**) at your local
Unsloth Studio server instead of GitHub's cloud models. No GitHub sign-in or Copilot subscription
needed for this — only unrelated features (code completions, semantic search) still require one.

**Prerequisite:** a model already running via `unsloth-serve` on `:8888` (§5/§11).

**Add the model provider:** Command Palette → `Chat: Manage Language Models` (or the gear icon in the
Copilot Chat model picker) → **Add Models** → provider **Custom Endpoint**. VS Code opens
`chatLanguageModels.json` — add this entry (provider + model together, as of VS Code 1.128+):

```json
{
  "name": "Unsloth Local",
  "vendor": "customendpoint",
  "apiKey": "<your UNSLOTH_STUDIO_API_KEY, e.g. from ~/.zshenv>",
  "apiType": "chat-completions",
  "models": [
    {
      "id": "tashfene/Ornith-1.0-35B-MTP-Q4_K_M-GGUF",
      "name": "Ornith 1.0 (local)",
      "url": "http://127.0.0.1:8888/v1/chat/completions",
      "requestHeaders": {
        "Authorization": "Bearer <your UNSLOTH_STUDIO_API_KEY>"
      },
      "toolCalling": true,
      "vision": false,
      "maxInputTokens": 110000,
      "maxOutputTokens": 21072
    }
  ]
}
```

**Auth in both places:** `apiKey` at the provider level (used by VS Code's internal utilities), and
`Authorization` header in `requestHeaders` (used by chat/agent API requests). Both should use the
same key. `maxInputTokens + maxOutputTokens` should sum to the context window you're serving (`-c
131072` in `unsloth-serve` → 110000 + 21072). `vision: false` because none of the fleet models are
vision-capable. The `id` is the served model's alias — this example is `ornith`; if you serve a
different model just change `id`/`name` to match (the local server only ever has one loaded, so the
exact string is mostly a label). Save, restart VS Code if the model doesn't appear, then select it.

**Fix the "utility model" error:** the first chat with a BYOK model usually hits:
> No utility model is configured for 'copilot-utility-small' while the selected main agent model is BYOK.

VS Code uses small internal "utility models" in the background (tool-selection routing, chat
titles, etc.), separate from your main chat model. Fix: Settings → search `Chat: Byok Utility Model Default` → change the dropdown from `GitHub Copilot` to your local model (e.g. `Qwen3.6 (local)`).

> Known issue: an open VS Code regression (microsoft/vscode#325150) can still hard-block the very
> first message even after setting this. If it happens, send a second message in the same chat
> session — subsequent turns work.

Your local model is now usable in chat, inline chat, and Agent mode.

---

## Known problems

- **OpenCode / VS Code Copilot: "Invalid or expired API key".** Almost never the key. Either no model
  is serving on `:8888` (run `unsloth-serve ornith`, wait for "model loaded") or `UNSLOTH_STUDIO_API_KEY`
  isn't set in this shell (open a new terminal / `source ~/.zshenv`; check with `unsloth-key`). See §7.
- **HuggingFace downloads fail on the VPN.** Try `hf auth login` first (a free token unblocked it for
  the team), *then* the CA-bundle fix in §10 if it's still failing.
- **`:8888` "in use" doesn't fail loud.** Launching a second model while one is live makes Studio
  silently bind the *next* free port (`:8889`…) — OpenCode still points at `:8888` and gets nothing.
  **Always Ctrl-C the running model first.**
- **Requests hang / 502, GPU at 0 %.** Either the `--no-context-shift` freeze (see §6 — the
  `limit.context` fix prevents it; restart the OpenCode agent to recover) or a **zombie Studio**
  whose `llama-server` child died. Diagnose:
  ```bash
  lsof -nP -iTCP:8888 -sTCP:LISTEN
  ps -ef | grep -E "unsloth studio|llama-server" | grep -v grep
  ```
  No live `llama-server` child = zombie → `kill <studio-pid>`, then `unsloth-serve ornith`. Note a
  Studio parent can also outlive its child on the internal port — check for an orphaned
  `llama-server` still holding memory after you stop it.
- **`failed to parse grammar` in the log** = the tool-call JSON grammar failed for that request. If
  it's constant with an MTP model, your **Studio is stale — update it** (`curl … unsloth.ai/install.sh | sh`).
- **MTP "doesn't help"?** Confirm `~/.unsloth/llama.cpp/llama-server --version` says *"Compiled by
  the Unsloth team"*. Stock llama.cpp won't accelerate `-MTP-` GGUFs.
- **Flaky tool calls?** Thinking-on models occasionally emit malformed `<tool_call>` XML. A/B by
  serving with thinking off before blaming the model.
- **`hf` shim breaks in scripts.** The pyenv `hf` shim can fail in non-interactive shells; call the
  real binary (`~/.pyenv/versions/*/bin/hf`) or the `uv`-installed one if a script download hangs.
- **Studio install takes 20+ min then says "limited: llama.cpp unavailable", or errors with `SSL:
  CERTIFICATE_VERIFY_FAILED … Missing Authority Key Identifier`.** Not a problem with your machine
  or a security concern — GlobalProtect's normal SSL inspection plus Python 3.13's stricter cert
  checks trip up two Python-driven downloads inside Unsloth's installer (nothing else — curl,
  Homebrew, npm are unaffected). Fix: `npm install -g npm@latest` (need ≥11) and `brew install
  cmake`, then re-run the install one-liner — see step 2 above and `UNSLOTH-CHEATSHEET.md`. No IT
  ticket or VPN disconnect needed.
- **`venv not found at ~/.unsloth/studio/unsloth_studio`, folder exists anyway.** Studio's venv
  Python can be a symlink into a Homebrew `python@3.X` rather than a real copy; if that formula
  later gets removed (e.g. `brew autoremove` after an unrelated uninstall) the symlink dangles and
  this misleading error appears. `brew install python@3.X` (same version) fixes it, or delete the
  venv folder and re-run install.sh.

---

*This mirrors Denis's working local-coding setup, with personal infrastructure removed. Ping him
with questions. Companion: **UNSLOTH-CHEATSHEET.md** (Studio/unsloth commands + links).*
