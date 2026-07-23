# Local LLM Coding on a Mac — Unsloth Studio + OpenCode

A step-by-step guide to running a capable coding model **fully locally** on Apple Silicon and wiring it into [OpenCode](https://opencode.ai) as an agentic coding assistant. This is the exact setup Denis runs day-to-day; the numbers below come from an **M4 Max / 36 GB**.

**What you get:** a private, offline-capable coding agent (tool calling, reasoning, ~85 tok/s) with no per-token cost and no data leaving your machine.

---

## 0. Prerequisites

| Requirement | Notes |
|---|---|
| **Apple Silicon Mac** (M1–M4) | Intel Macs won't get Metal GPU acceleration — don't bother. |
| **Unified memory** | The 35B daily driver needs a **~27 GB working set**. On **36 GB+** it's comfortable. On **24 GB**, run a smaller model (see §7). On 16 GB, local coding isn't really viable. |
| **Free disk** | ~20–30 GB per model quant. |
| **`hf` CLI** | For model downloads. `pip install "huggingface_hub[cli]"` (or it comes with most Python setups). |
| **OpenCode** | `curl -fsSL https://opencode.ai/install \| bash` — [docs](https://opencode.ai/docs). |

Check your memory: ` ` (Apple menu → About This Mac), or `sysctl hw.memsize`.

---

## 1. Install Unsloth Studio

One line (same command updates it later):

```bash
curl -fsSL https://unsloth.ai/install.sh | sh
```

This drops a **self-contained bundle** in `~/.unsloth/` — its own Python venv, a bundled `llama.cpp` (the actual inference engine), and a small web UI. Nothing touches your system Python. It puts a launcher at `~/.local/bin/unsloth`, so make sure `~/.local/bin` is on your `PATH`.

Verify:

```bash
unsloth --version   # e.g. 2026.6.9
```

> Unsloth Studio is a wrapper around `llama.cpp`'s `llama-server`. It serves an **OpenAI-compatible** endpoint, which is what lets OpenCode talk to it.

> ### ⚠️ Why it has to be Unsloth Studio (the MTP catch)
> The daily-driver model is an **MTP** ("Multi-Token Prediction") variant, and **the MTP GGUF format only loads and accelerates on Unsloth Studio's *patched* `llama.cpp` build** (it identifies itself as *"Compiled by the Unsloth team"*, v9871+). Stock `llama.cpp`, LM Studio, and older Studio versions either **fail to load the MTP format** or throw `failed to parse grammar` / show no speculative speedup — this is the single biggest gotcha, and it's why the disputed "MTP is net-negative on Metal" reports exist (they were run on unpatched builds).
>
> **Resolution: keep Unsloth Studio up to date.** Re-running the install one-liner updates it and pulls the current patched engine:
> ```bash
> curl -fsSL https://unsloth.ai/install.sh | sh   # installs AND updates
> ```
> You can confirm the patched build with `~/.unsloth/llama.cpp/build/bin/llama-server --version` — it should say *"Compiled by the Unsloth team"*. If you don't need MTP, a plain (non-MTP) GGUF works on any `llama.cpp`, but you lose the ~1.5–2× speculative-decoding speedup.

---

## 2. Download a model

The daily driver is **Qwen3.6 35B A3B (MTP variant)** — a Mixture-of-Experts model (35B total, ~3B active per token, so it's fast) with **MTP speculative decoding** baked in for extra speed. We use Unsloth's `UD-Q4_K_XL` quant (their "Unsloth Dynamic" Q4 — the quality floor for reliable tool calling; don't go below Q4 for agentic work).

The `--include` glob pulls **only** that one quant, not the whole multi-quant repo (which is hundreds of GB):

```bash
# Optional but recommended — faster downloads for 20 GB+ files:
pip install "huggingface_hub[hf_transfer]" && export HF_HUB_ENABLE_HF_TRANSFER=1

# ~19 GB — the daily driver
hf download unsloth/Qwen3.6-35B-A3B-MTP-GGUF --include "*UD-Q4_K_XL*"
```

Files land in `~/.cache/huggingface/hub`, which is exactly where Studio's `--model` flag looks. (You can also skip this step — Studio auto-downloads on first `run` — but pre-downloading keeps the wait out of your first session.)

---

## 3. Create the launch script

Codify the serving config in one script so you're not retyping flags. Save as `~/bin/unsloth-serve` (make sure `~/bin` is on your `PATH`):

```bash
#!/bin/bash
# Canonical Unsloth Studio launch — Qwen3.6-35B-A3B MTP for OpenCode.
# Studio auto-adds MTP speculative decoding (ngram-mod,draft-mtp) for MTP models.
exec ~/.local/bin/unsloth studio run \
  --model unsloth/Qwen3.6-35B-A3B-MTP-GGUF \
  --gguf-variant UD-Q4_K_XL \
  --disable-tools \
  --parallel 1 \
  -p 8888 \
  -c 131072 \
  -ngl 99 \
  -ctk q8_0 -ctv q8_0 \
  --no-mmproj \
  --reasoning on \
  --chat-template-kwargs '{"enable_thinking":true,"preserve_thinking":false}'
```

Then:

```bash
chmod +x ~/bin/unsloth-serve
unsloth-serve          # starts the server on http://127.0.0.1:8888
```

**What each flag does (and why it matters):**

| Flag | Why |
|---|---|
| `--gguf-variant UD-Q4_K_XL` | Picks the quant. Q4-class is the floor — Q3 correlates with malformed tool calls. |
| `--disable-tools` | Disables Studio's **server-side** tools (web search / code exec). **Does NOT disable client tool calling** — OpenCode still gets full tool use. Correct for this setup. |
| `--parallel 1` | Single slot → the prompt cache isn't split. Agentic prompts are long; you want them all cached. |
| `-c 131072` | 131k context. Cheap on this model — its hybrid attention needs only ~1.3 GB of KV cache at this length (a dense model would need far more). |
| `-ngl 99` | Offload all layers to the Metal GPU. |
| `-ctk q8_0 -ctv q8_0` | 8-bit KV cache — halves KV memory with negligible quality loss. |
| `--no-mmproj` | Skips loading the vision projector — saves memory, you don't need images for coding. |
| `--reasoning on` + `enable_thinking:true` | **Thinking mode ON.** Denis measured noticeably better results with it. If your tool calling gets flaky, this is the first thing to A/B toggle off. |

Leave this terminal running (or set it up as a background service later — see §8).

---

## 4. Wire it into OpenCode

OpenCode needs a **custom provider** pointing at the local server. Edit `~/.config/opencode/opencode.json` and add this to the `provider` block:

```jsonc
{
  "provider": {
    "unsloth-studio": {
      "name": "Unsloth Studio",
      "npm": "@ai-sdk/openai-compatible",
      "env": ["UNSLOTH_STUDIO_API_KEY"],
      "options": {
        "baseURL": "http://127.0.0.1:8888/v1",
        "apiKey": "{env:UNSLOTH_STUDIO_API_KEY}"
      },
      "models": {
        "unsloth/Qwen3.6-35B-A3B-MTP-GGUF": {
          "name": "Qwen3.6 35B A3B MTP (thinking)"
        }
      }
    }
  }
}
```

The API key is **localhost-only** — it's just what Studio's endpoint expects, not a secret you pay for. Keep it out of the JSON; put it in your shell env (`~/.zshenv`):

```bash
export UNSLOTH_STUDIO_API_KEY="sk-unsloth-<whatever-your-studio-instance-uses>"
```

(Your Studio instance prints/uses its own key; for a localhost server any non-empty value it accepts is fine.) Restart your terminal so the export is live.

**Set it as your default model** (top of `opencode.json`) — the format is `<provider-key>/<model-id>`:

```jsonc
{
  "model": "unsloth-studio/unsloth/Qwen3.6-35B-A3B-MTP-GGUF"
}
```

Now launch OpenCode in any project and it's talking to your local model.

---

## 5. Verify it works

Quickest check — a raw request to the endpoint:

```bash
curl -s http://127.0.0.1:8888/v1/chat/completions \
  -H "Authorization: Bearer $UNSLOTH_STUDIO_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"unsloth/Qwen3.6-35B-A3B-MTP-GGUF","messages":[{"role":"user","content":"say hi in 3 words"}]}' \
  | python3 -m json.tool
```

For a real check that **tool calling** works (the thing that makes or breaks an agentic model), there's a 6-scenario smoke test in this repo:

```bash
uv run bench/smoke_test.py          # hits 127.0.0.1:8888 by default
```

On the M4 Max this scores **6/6 pass, ~87 tok/s median**. Read `bench/README.md` for flags.

---

## 6. What to expect (M4 Max / 36 GB numbers)

- **Generation:** 34–50 tok/s in long agentic sessions, ~87 tok/s on short prompts.
- **Prefill (prompt processing):** ~200–400 tok/s — **this is the real bottleneck**, not generation. Long OpenCode prompts dominate latency, which is why `--parallel 1` (full prompt cache) matters.
- **Memory:** ~26–28 GB working set. That's right at the macOS Metal "wired memory" cap (~75% of RAM). If you hit OOM or heavy swapping, raise it:
  ```bash
  # e.g. allow 30 GB wired on a 36 GB machine (resets on reboot):
  sudo sysctl iogpu.wired_limit_mb=30720
  ```

---

## 7. Adjusting for your Mac

The config above assumes ~36 GB. Scale the model to your memory:

| Your RAM | Suggested model | Repo (`--gguf-variant UD-Q4_K_XL`) | Working set |
|---|---|---|---|
| **48 GB+** | Same 35B, or go higher context | `unsloth/Qwen3.6-35B-A3B-MTP-GGUF` | ~27 GB |
| **32–36 GB** | The 35B daily driver | `unsloth/Qwen3.6-35B-A3B-MTP-GGUF` | ~27 GB |
| **24 GB** | Gemma 4 26B-A4B (fast) or GLM-4.7-Flash | `unsloth/gemma-4-26B-A4B-it-GGUF` / `unsloth/GLM-4.7-Flash-GGUF` | ~17–18 GB |
| **16 GB** | Not really viable for agentic coding | — | — |

On less memory, also drop `-c 131072` to something like `-c 32768` to shave KV cache.

**Other strong local coding models** (same download/serve pattern, just swap `--model` + `--gguf-variant`):
- **GLM-4.7-Flash** (`unsloth/GLM-4.7-Flash-GGUF`) — best tool-calling in the 30B class; **smoke-verified here 6/6 at ~65 tok/s** (UD-Q5_K_XL, non-MTP). A genuine second agentic-coding driver alongside the Qwen daily driver — slower, higher coding quality.
- **Gemma 4 26B-A4B-it** (`unsloth/gemma-4-26B-A4B-it-GGUF`) — fastest of the three, tool calling reported to work well in Studio.

> **Want the MTP speed boost on these too?** As of now (2026-07) **Unsloth doesn't publish official MTP GGUFs** for GLM-4.7-Flash or Gemma 4 A4B — only *community* MTP quants exist (e.g. `jacek2024/GLM-4.7-Flash-MTP-GGUF`, `ironbcc/gemma-4-26B-A4B-it-MTP-GGUF`). Two caveats before using them: (1) they're not Unsloth's dynamic-quant recipe, so quality is less certain; (2) MTP only accelerates if Studio's patched `llama.cpp` implements MTP draft *for that architecture* — confirmed for Qwen3.6, **unverified for GLM/Gemma**. Treat them as an A/B experiment (measure `draft acceptance` in the log), not a default. The **Qwen3.6-35B-A3B-MTP** daily driver is the one with confirmed, first-party MTP support.

---

## 8. Nice-to-haves

- **Run on login:** wrap `~/bin/unsloth-serve` in a `launchd` LaunchAgent (`~/Library/LaunchAgents/`) so the server starts at boot. Optional — most people just run the script when they sit down to work.
- **Watch the logs:** `~/.unsloth/studio/logs/llama-server/*.log` has the real tok/s, draft-acceptance rates, and any tool-call grammar errors — the first place to look when something's slow or flaky.
- **Inline prefill progress bar:** Studio prints only its own JSON to the serve terminal and hides `llama-server`'s native stdout in the logfile above — so you *don't* see the LM-Studio-style "processing prompt" bar. `~/bin/unsloth-serve` fixes this: for Studio-served models it tails the new logfile in the background and echoes the incremental `prompt processing … progress = 0.XX` line (and gen tok/s) into the *same* terminal, then cleans up on exit. No second terminal needed. Note it only appears for prefills ≥3 s (same as LM Studio — tiny prompts show nothing); direct-served models like gpt-oss/North-Mini print it natively.
- **Web UI:** Studio also serves a browser UI for chatting/managing models — the launch output prints the URL.

---

## Gotchas (learned the hard way)

- **`--disable-tools` is a trap name** — it disables *server-side* tools only. Client tool calling (what OpenCode uses) still works. Leave it on.
- **MLX vs GGUF:** you may see MLX quants recommended for Apple Silicon. They can be great, but MLX *runtime* bugs (OOM crashes, KV-cache arch gaps) have masqueraded as "the model is broken" — GGUF-on-llama.cpp (what Studio uses) has been the more reliable path here. Don't judge a model by one runtime's build failing.
- **Thinking mode & tool calls:** always-thinking models occasionally emit malformed `<tool_call>` XML. If tool calling degrades, A/B `enable_thinking:false` before blaming the model.
- **"failed to parse grammar"** in the server log = the tool-call JSON grammar build failed for that request. Usually a `llama.cpp` version issue or an over-nested tool schema — not the model. **If you see it constantly with an MTP model, your Studio is stale — update it** (see §1's MTP callout).
- **MTP needs Unsloth Studio's patched engine.** The `-MTP-` GGUFs won't accelerate (or won't load) on stock `llama.cpp` / LM Studio. If MTP "doesn't help," check `llama-server --version` says *"Compiled by the Unsloth team"* and update Studio if not.
- **Quant floor:** UD-Q4_K_XL is the lowest you should go for agentic use. Q3-class quants correlate with broken tool calls.

---

*Questions? This mirrors Denis's working setup — ping him. The companion "Silicon Bench" dashboard in this repo (`index.html`) logs which models actually earned a spot in the rotation.*
