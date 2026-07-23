# Unsloth Studio — cheat-sheet

Everything you routinely need for the local serving layer, in one page. Unsloth Studio is a wrapper
around a **patched `llama.cpp`** that serves GGUF models over an **OpenAI-compatible** endpoint on
`:8888` — which is what lets OpenCode / Copilot / `curl` talk to a local model.

## FAQ: why GGUF, not MLX?

Short answer: reliability for agentic work, not model quality. Several models that looked "broken"
on MLX (LM Studio) turned out to be runtime bugs — the identical weights ran clean on GGUF:

- **GLM-4.7-Flash crashed at 0% prompt processing on MLX**, escalating to a macOS kernel panic once
  — its MLA/latent-KV attention expects a plain-array KV cache, but MLX's "KV Cache Quantization"
  setting returns a tuple instead. Same gap hits DeepSeek V3 and Kimi K2.5 on MLX.
- **The Opus-reasoning distill had multi-turn tool-calling degradation and OOM crashes on MLX** —
  clean on GGUF.
- **MTP speculative decoding (~1.4–2.2× faster generation) only works on Unsloth's patched
  llama.cpp** — it doesn't accelerate on MLX at all.

Not a claim that MLX is bad — it wins on raw decode speed for single-model chat. For agentic work
(long contexts, tool-calling), GGUF/llama.cpp was the more mature runtime here. If MLX works for
you already, no need to switch.

## FAQ: why Unsloth Studio, not Ollama?

Ollama also serves local GGUF models, so this is a fair follow-up. Short version: Unsloth trades
some integration convenience for a more capable engine, better quant quality, and fresher models.

- **MTP speculative decoding** (~1.4–2.2× faster generation) only works on Unsloth Studio's patched
  `llama.cpp`. Ollama's own engine doesn't expose it — mainline llama.cpp features often land in
  Ollama later, if at all.
- **Quant quality:** Unsloth's `UD-...` ("Dynamic") quants selectively keep more bits on sensitive
  layers instead of uniform quantization — measurably better quality at the same file size than a
  naive quant. Ollama's library serves whatever quant got uploaded, with no equivalent step.
- **Model freshness:** Unsloth typically ships GGUFs same-day for new open-weight releases. Ollama's
  library depends on re-packaging into Ollama's format, often lagging days to weeks.
- **Config ergonomics:** context window, KV-cache quant, chat-template kwargs, reasoning toggle are
  all plain CLI flags on `unsloth-serve`. Ollama needs env vars edited inside a **version-pinned**
  Homebrew plist file for something as basic as context length — breaks on every Ollama update.

**Where Ollama wins:** out-of-the-box integration — `ollama launch claude/opencode/codex/copilot`
is a one-liner, plus a native VS Code extension. This setup needed custom tooling (`unsloth-serve`,
`copilot-local`, the VS Code Custom Endpoint config) to get the same reach.

## Links

| What | URL |
|---|---|
| Unsloth Studio (install, docs) | <https://unsloth.ai> · install: `curl -fsSL https://unsloth.ai/install.sh \| sh` |
| Unsloth docs hub | <https://docs.unsloth.ai> |
| Unsloth GGUF models (HuggingFace) | <https://huggingface.co/unsloth> |
| OpenCode | <https://opencode.ai> · <https://opencode.ai/docs> |
| GitHub Copilot CLI (`@github/copilot`) | <https://www.npmjs.com/package/@github/copilot> · <https://docs.github.com/copilot> |
| llama.cpp (the engine underneath) | <https://github.com/ggml-org/llama.cpp> |
| Full local-LLM setup guide | `../docs/local-llm-setup-guide.md` |

## Install / update / where things live

```bash
curl -fsSL https://unsloth.ai/install.sh | sh    # installs AND updates (same line)
unsloth --version                                 # e.g. 2026.6.9
```

| Path | What |
|---|---|
| `~/.local/bin/unsloth` | the CLI launcher |
| `~/.unsloth/llama.cpp/llama-server` | the patched engine (`--version` says *"Compiled by the Unsloth team"*) |
| `~/.cache/huggingface/hub/models--*` | downloaded model weights (GGUF) |
| `~/.unsloth/studio/logs/llama-server/*.log` | real tok/s, draft-acceptance, tool-call grammar errors |
| `~/.unsloth/studio/auth/agent_api_key.json` | Studio's minted localhost key (`install.sh` uses it if present; any non-empty value also works — run `unsloth-key` to see yours) |

> **Keep Studio updated.** The MTP (`-MTP-`) GGUFs only load/accelerate on the patched engine; a
> stale Studio is the #1 cause of `failed to parse grammar` and "MTP doesn't help".

## Typical `unsloth` commands

```bash
# Serve a model (what ~/bin/unsloth-serve wraps). Downloads on first run if missing.
unsloth studio run --model unsloth/Qwen3.6-35B-A3B-MTP-GGUF --gguf-variant UD-Q5_K_S -p 8888

unsloth studio run --help          # every serving flag (auth, context, GPU, UI, TLS …)
unsloth --help                     # top-level command list
unsloth studio                     # launch the browser UI (chat + manage models)
```

Key `studio run` flags (see the launcher for the full per-model set):

| Flag | Meaning |
|---|---|
| `--model <repo>` `--gguf-variant <Q>` | which HF repo + which quant to serve |
| `-p 8888` / `-H 127.0.0.1` | port / host |
| `-c 131072` / `--max-seq-length` | context window |
| `-ngl 99` | offload all layers to the Metal GPU |
| `-ctk q8_0` | 8-bit KV cache (halves KV memory; Studio mirrors it to V) |
| `--reasoning on\|off` | thinking mode |
| `--disable-tools` | disables Studio's **server-side** tools only — **client tool calling still works** (leave it on) |
| `--parallel 1` | single slot → full prompt cache (agentic prompts are long) |
| `--chat-template-kwargs '{…}'` | model-specific template knobs (e.g. `reasoning_effort`, `enable_thinking`) |

> Studio silently appends flags you didn't write (`--no-context-shift`, `--flash-attn on`,
> `--jinja`, `--fit …`, `--parallel 1`, `--metrics`) and **rejects** attempts to override some of
> them. The one that bites: `--no-context-shift` (see the launcher / INSTALL.md §6).

## Downloading models (`hf`)

```bash
uv tool install "huggingface_hub[cli]"   # get the `hf` CLI
hf auth login                            # free token → huggingface.co/settings/tokens (unblocks VPN downloads)
export HF_XET_HIGH_PERFORMANCE=1         # fast Xet-backend downloads

# --include pulls ONLY that quant (repos hold many — don't grab the whole thing)
hf download unsloth/Qwen3.6-35B-A3B-MTP-GGUF --include "*UD-Q5_K_S*"

hf download --help          # resume, revision, local-dir, token, etc.
```

> **Downloads fail on the VPN?** Log in first — `hf auth login`. Anonymous pulls get rate-limited /
> rejected through the corporate TLS proxy, and a free HuggingFace token is what unblocked downloads
> for the team. Only if that doesn't help, reach for the CA-bundle fix in the next note.
> (`HF_HUB_ENABLE_HF_TRANSFER=1` from older guides is now a deprecated no-op — the Hub moved to the
> Xet backend; `HF_XET_HIGH_PERFORMANCE=1` is the modern equivalent.)

> **Behind a corporate VPN, downloads fail with `certificate verify failed: self-signed certificate in
> certificate chain`.** `hf` (Python/httpx) doesn't use the macOS trust store — point it at your
> corporate CA bundle (if you're behind a TLS-intercepting proxy; same one Node uses via `NODE_EXTRA_CA_CERTS`):
> ```bash
> export SSL_CERT_FILE="$HOME/.ssl/allCAbundle.pem"
> export REQUESTS_CA_BUNDLE="$HOME/.ssl/allCAbundle.pem"
> ```
> Add both to `~/.zshenv` to persist. ⚠️ The file must exist — if `SSL_CERT_FILE` points at a
> missing path, *every* Python/httpx tool dies with `FileNotFoundError`, not just downloads.

## Serving with the launcher (`~/bin/unsloth-serve`)

```bash
unsloth-serve ornith     # #1 overall (benchmark 88.3) — start here
unsloth-serve gemma      # #2 — fastest + cleanest tools
unsloth-serve qwopus     # #3 — best pure coder
unsloth-serve opus       # #4 — safest proven daily driver (Opus-4.6 distill)
unsloth-serve glm        # #5 — high quality, slower
unsloth-serve northmini  # #6 — agentic, OpenCode-trained
unsloth-serve            # qwen — #7, launcher's no-arg default (best raw coding)
unsloth-serve gpt-oss    # #9 — smallest/fastest, ~13 GB tiny-RAM pick
```

Ranked by **the benchmark** — see the benchmark leaderboard ([LEADERBOARD.md](../docs/leaderboard.md)). **One model at a time** —
36 GB holds exactly one. Stop the running one (**Ctrl-C**) before switching, or Studio silently
binds `:8889` and clients (still on `:8888`) get nothing.

The launcher streams an **inline prefill progress bar** for Studio models (`gemma`/`opus`/`glm`/`qwen`) — it
tails Studio's hidden llama-server log and echoes the `progress = 0.XX` line into your terminal:
```
prompt processing, n_tokens = 6144, progress = 0.66, t = 66.95 s / 91.77 tokens per second
```
Only shows for prefills ≥3 s (like LM Studio); `gpt-oss`/`northmini` print it natively.

## Copilot CLI on the local model (BYOK)

Plain `copilot` keeps your normal GitHub/enterprise auth. `copilot-local [key]` (installed into
`~/.zshenv` by the setup, needs Copilot CLI **2026.04+**) is a wrapper that points that one
invocation at the local Unsloth endpoint instead — no GitHub auth needed, works offline:
```bash
copilot-local -p "say hi in 3 words" --allow-all-tools -s        # default key = qwen
copilot-local glm -p "say hi in 3 words" --allow-all-tools -s    # label it as glm
```
It's a plain shell function (`copilot "$@"` with `COPILOT_PROVIDER_BASE_URL` / `COPILOT_MODEL`
set) — see `copilot help providers` for the full BYOK env-var reference. We don't export those
vars globally because `COPILOT_PROVIDER_BASE_URL` disables GitHub auth for **every** `copilot`
call the moment it's set in the shell.

**`key` only picks the *label* sent as `COPILOT_MODEL` — it does not load a model.** Exactly like
OpenCode, only one model is ever live on `:8888` (one `unsloth-serve` process, 36 GB = one
model). Run `unsloth-serve <key>` first to actually load that model into RAM; `copilot-local
<key>` then just needs to agree with it so Copilot's token/context-limit lookup is accurate — the
server itself doesn't check the `model` field, it always answers with whatever's currently
loaded.

## VS Code Copilot Chat (BYOK)

Point VS Code's Copilot Chat extension (chat panel, inline chat, **and Agent mode**) at your local
model instead of GitHub's cloud models — no GitHub sign-in or Copilot subscription needed for
this. Requires Copilot Chat's **Custom Endpoint** BYOK provider (current since ~VS Code 1.120+).

**Add the model:** Command Palette → `Chat: Manage Language Models` (or the gear icon in the
Copilot Chat model picker) → **Add Models** → provider **Custom Endpoint** → `apiType:
chat-completions`. VS Code opens `chatLanguageModels.json` — add an entry:

```json
{
  "id": "unsloth-ornith",
  "name": "Ornith 1.0 (local)",
  "url": "http://127.0.0.1:8888/v1/chat/completions",
  "apiType": "chat-completions",
  "apiKey": "<your UNSLOTH_STUDIO_API_KEY, e.g. from ~/.zshenv>",
  "toolCalling": true,
  "vision": false,
  "maxInputTokens": 110000,
  "maxOutputTokens": 21072
}
```

`maxInputTokens + maxOutputTokens` should sum to whatever context window you're serving with (`-c
131072` in `unsloth-serve` → 110000 + 21072). `vision: false` — none of the fleet models are
vision-capable. Restart VS Code if the model doesn't show up in the picker, then select it.

**"No utility model configured for 'copilot-utility-small'" on first message:** VS Code uses small
internal "utility models" in the background (tool-selection routing, chat titles, etc.), separate
from your main chat model, and doesn't default these to a BYOK model. Fix: Settings → search
`utility` → **Chat: Byok Utility Model Default** → set the dropdown to your local model (e.g.
`Ornith 1.0 (local)`) instead of `GitHub Copilot`. If it still hard-blocks the very first message
after that, it's a known open VS Code regression (microsoft/vscode#325150) — send a second message
in the same session and it clears up.

Once configured, the model works in chat, inline chat, and Agent mode (Agent mode needs
`toolCalling: true` — verified working against this server's `/v1/chat/completions`).

## Health checks

```bash
# Is a model serving? (list models on the endpoint)
curl -s http://127.0.0.1:8888/v1/models \
  -H "Authorization: Bearer $UNSLOTH_STUDIO_API_KEY" | python3 -m json.tool

# A real completion
curl -s http://127.0.0.1:8888/v1/chat/completions \
  -H "Authorization: Bearer $UNSLOTH_STUDIO_API_KEY" -H "Content-Type: application/json" \
  -d '{"model":"unsloth/Qwen3.6-35B-A3B-MTP-GGUF","messages":[{"role":"user","content":"hi"}]}' \
  | python3 -m json.tool

# Who holds the port / is there a live engine?
lsof -nP -iTCP:8888 -sTCP:LISTEN
ps -ef | grep -E "unsloth studio|llama-server" | grep -v grep

# GPU memory cap
sysctl iogpu.wired_limit_mb
```

## When something's wrong

| Symptom | Likely cause → fix |
|---|---|
| OpenCode / VS Code Copilot: "Invalid or expired API key" | **Not the key.** No model on `:8888` (`unsloth-serve ornith`, wait for "model loaded") **or** `UNSLOTH_STUDIO_API_KEY` unset in this shell (new terminal / `source ~/.zshenv`; check with `unsloth-key`) |
| Requests hang, GPU at 0 % | `--no-context-shift` freeze → restart the OpenCode agent; keep `limit.context:90000` in `opencode.json` |
| 502 / nothing on :8888 but port is LISTENing | zombie Studio (engine child died) → `kill <studio-pid>`, `unsloth-serve ornith` |
| Second `unsloth-serve` "works" but OpenCode gets nothing | it bound `:8889` → Ctrl-C the first one, restart |
| `failed to parse grammar` (constant, MTP model) | stale Studio → `curl … unsloth.ai/install.sh \| sh` |
| MTP gives no speedup | wrong engine → `~/.unsloth/llama.cpp/llama-server --version` must say *"Compiled by the Unsloth team"* |
| Flaky/malformed `<tool_call>` XML | thinking-on artefact → A/B serve with `--reasoning off` |
| OOM / heavy swap | raise `iogpu.wired_limit_mb` via install.sh step 8 (scales to `(your RAM − 4 GB)`, don't hand-set it higher), restart the model |
| `hf download` fails with `SSL: CERTIFICATE_VERIFY_FAILED … self-signed certificate in certificate chain` | **First** try `hf auth login` (a free token unblocked it for the team). Still failing = a corporate TLS-inspecting proxy; `hf` (Python/httpx) ignores the macOS trust store → point it at your corporate CA bundle, `export SSL_CERT_FILE="$HOME/.ssl/allCAbundle.pem"` and `REQUESTS_CA_BUNDLE` too, re-run. Persist in `~/.zshenv`. The path must exist or *all* Python tools throw `FileNotFoundError`. `install.sh` fails loud (no false "done") and prints this fix. See INSTALL.md §10 |
| Studio install hangs ~20+ min then either works or ends "limited: llama.cpp unavailable", or you see `SSL: CERTIFICATE_VERIFY_FAILED … Missing Authority Key Identifier` | Not a bug or a security problem — GlobalProtect's normal SSL inspection combined with Python 3.13's stricter certificate checks trips up two Python-driven downloads inside Unsloth's installer (Node, and the prebuilt llama.cpp binary). curl, Homebrew, and npm registry installs are all unaffected — this is specific to Python's urllib. `install.sh` auto-fixes both halves (npm≥11 so Node is reused instead of downloaded; `cmake` so llama.cpp falls back to a local source build) — just let it run, it's not stuck, it just takes ~20–25 min instead of a couple while llama.cpp compiles. Running Unsloth's installer standalone (not via `install.sh`)? Make sure `npm -v` is ≥11 and `cmake` is installed first, same fix. No IT ticket or VPN disconnect needed either way. |
| `venv not found at ~/.unsloth/studio/unsloth_studio` (re-run install.sh) even though the folder exists | the venv's `bin/python` can be a symlink straight into a Homebrew Python (`/opt/homebrew/opt/python@3.X/bin/python3.X`) rather than a copy — if that formula is later removed (e.g. by `brew autoremove` after uninstalling something unrelated) or upgraded to a different Cellar version, the symlink dangles and Studio misreports it as "not found". Fix: `brew install python@3.X` (same version) to restore the target, or delete `~/.unsloth/studio/unsloth_studio` and re-run install.sh to get a fresh venv. |
