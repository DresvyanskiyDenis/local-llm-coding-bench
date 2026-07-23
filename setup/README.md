# Local coding stack — team setup

Replicate Denis's **fully local, private coding agent** on your Mac: Unsloth Studio serves an
open-weight model on `localhost:8888`. Use it straight from **VS Code — GitHub Copilot Chat's
Custom Endpoint (BYOK)** — the primary path for most people, no Copilot subscription needed for it
— or from the CLI: **OpenCode** uses it by default, and **GitHub Copilot CLI** can too via
`copilot-local [key]`, while plain `copilot` keeps your normal GitHub/enterprise auth. Only one
model is ever loaded at a time. No per-token cost, no code leaving your machine.

**Target machine:** Apple Silicon Mac (M1–M4), ≥32 GB unified memory, macOS. (Same spec as Denis's.)

> 🛟 **Hit an error?** Jump to **Known problems** in `INSTALL.md` (VPN/SSL, "Invalid or expired
> API key", model downloads) — the three things people actually trip on are all answered there.

---

## Quick start — most people need only this

```bash
cd team-setup
./install.sh                 # interactive — say y to each step
```

Then, in order:

1. **Run `./install.sh`** and answer `y` to each step. It's idempotent — safe to re-run, it skips
   whatever's already there.
2. **Log in to HuggingFace when asked** — paste a free token from
   [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens). *This is what makes
   downloads work on the corporate VPN* — do it even if you think you don't need it.
3. **Pick a model to download** at the models prompt. Start with **`ornith`** (~22 GB) — the
   benchmark #1; you don't need all eight.
4. **Open a NEW terminal** (so `~/.zshenv` loads), then start the model:
   ```bash
   unsloth-serve ornith      # wait for "model loaded" — serves on :8888
   ```
5. **Use it in VS Code** — GitHub Copilot Chat → add the local model as a **Custom Endpoint (BYOK)**
   (one-time, ~2 min; steps in `INSTALL.md` §12 or `UNSLOTH-CHEATSHEET.md`). Then chat, inline chat,
   and Agent mode all run on your local model. *Prefer the terminal? Run `opencode` in any project —
   it uses the local model by default.* Done.

> **Stuck on "Invalid or expired API key" in OpenCode?** It's almost never the key — either no model
> is serving on `:8888` yet (do step 4 and wait for "model loaded"), or you're in a terminal opened
> *before* install finished (open a new one, or `source ~/.zshenv`; check with `unsloth-key`).
>
> **Want to see exactly what each step does, or run it by hand?** → **`INSTALL.md`** (the detailed
> path). Everything below is optional background.

---

## The model fleet

Ranked by **the benchmark** — see the benchmark leaderboard ([LEADERBOARD.md](../LEADERBOARD.md))
(450 test units, one M4 Max / 36 GB, fully local). The top 3:

| Rank | `unsloth-serve` | Model | Score | Role |
|---|---|---|---|---|
| 🥇 1 | `ornith` | Ornith-1.0 35B (Q4_K_M) | **88.3** | best overall — no weak axis |
| 🥈 2 | `gemma` | Gemma-4 26B-A4B (UD-Q5_K_XL) | **87.1** | fastest + cleanest tools |
| 🥉 3 | `qwopus` | Qwopus3.6 Coder (Q5_K_M) | **87.0** | best pure coder |

**Start with `unsloth-serve ornith`.** The zip ships **8 curated models** — these three plus `opus`
(#4, safest daily driver), `glm` (#5), `northmini` (#6), `qwen` (#7, the launcher default), and
`gpt-oss` (#9, the ~13 GB tiny-RAM pick). **Full ranking, scores and methodology for all 9 →
see the benchmark leaderboard ([LEADERBOARD.md](../LEADERBOARD.md)).**
Want something outside this set? Any GGUF in Unsloth's
[model catalog](https://unsloth.ai/docs/get-started/unsloth-model-catalog) can be added to
`unsloth-serve` the same way.

> **Behind a corporate VPN and downloads fail** with `certificate verify failed: self-signed
> certificate in certificate chain`? First `hf auth login` (a free token was the fix for the team);
> if it still fails, point the `hf` downloader at your corporate CA bundle (if you're behind a
> TLS-intercepting proxy), e.g. `export SSL_CERT_FILE="$HOME/.ssl/allCAbundle.pem"`
> (+ `REQUESTS_CA_BUNDLE`), then re-run. Full details: `INSTALL.md` §10.

---

## What gets installed

1. **Unsloth Studio** — patched `llama.cpp`, serves GGUF on `:8888` (`curl … unsloth.ai/install.sh | sh`)
2. **`~/bin/unsloth-serve`** — launcher for the 8-model fleet (one at a time; 36 GB holds one)
3. **OpenCode** — the agentic coding CLI, defaulting to the local model
4. **GitHub Copilot CLI** — `@github/copilot` (npm; **not** the AWS `copilot` brew formula)
5. **`~/.config/opencode/opencode.json`** — cleaned team config (no personal infra/keys)
6. **Shell env** — `PATH` + `UNSLOTH_STUDIO_API_KEY` (+ an `unsloth-key` helper) in `~/.zshenv`
7. *(opt-in, sudo)* **GPU wired-limit daemon** — raises the Metal cap to `(your RAM − 4 GB)`
8. *(opt-in)* **Login autostart** — boots the default model at login

## Two ways to install — pick by how much you trust a script

| | Automated | Manual |
|---|---|---|
| **File** | `install.sh` | `INSTALL.md` |
| **For** | "just set it up, ask me at each step" | "I want to run each command and see what it does" |
| **How** | asks `[y/N]` before every step; lets you tick which models to download | copy-paste, step by step, with a "check first" before each |

Both install the **identical** files from `assets/`, so you can mix them (script most of it, do one
step by hand).

```bash
./install.sh --auto                 # unattended; skips model downloads + sudo/login tweaks
./install.sh --auto --with-system   # unattended; ALSO does GPU-limit (sudo) + login autostart
./install.sh --help
```

The script is **idempotent** — it detects what's already installed and skips it, so re-running is
safe.

## Files in this folder

```
team-setup/
├── README.md              ← you are here (quick start + overview)
├── install.sh             ← automated installer (heavily commented)
├── INSTALL.md             ← full manual instructions (super-detailed)
├── UNSLOTH-CHEATSHEET.md  ← Unsloth Studio commands, flags, health checks, links
├── index.html             ← offline model-comparison snapshot (see the benchmark leaderboard, LEADERBOARD.md, linked above)
└── assets/                ← the actual files the installer/manual put in place
    ├── unsloth-serve
    ├── opencode.json
    ├── com.user.unsloth-studio.plist
    └── local.unsloth.iogpu-wired-limit.plist
```

## After install

```bash
# new terminal (loads ~/.zshenv), then:
unsloth-serve ornith   # serve the benchmark #1 model on :8888
# → primary: use it in VS Code — Copilot Chat → Custom Endpoint (BYOK), see INSTALL.md §12
# → or from the CLI:
opencode               # in any project — talks to the local model by default
copilot-local -p "..."  # optional: Copilot CLI on the local model instead of GitHub's cloud
                         # (copilot-local qwen -p "..." if you ran `unsloth-serve qwen` instead)
```

## VS Code Copilot Chat (BYOK) — the primary client

For most people this is how you use the local model day-to-day. VS Code's GitHub Copilot Chat
extension talks to your local endpoint — chat panel, inline chat, and **Agent mode** — via its
**Custom Endpoint (BYOK)** provider; no Copilot subscription or GitHub sign-in needed for it. Full
step-by-step: `INSTALL.md` §12 or `UNSLOTH-CHEATSHEET.md` → "VS Code Copilot Chat (BYOK)".

---

## Background — why these choices *(optional reading)*

You don't need any of this to use the setup — it's here for the "but why GGUF / why not Ollama?"
questions.

### Why GGUF (via Unsloth Studio), not MLX?

If you're coming from LM Studio + MLX and wondering why this setup uses a different format —
short answer: reliability for *agentic* work, not model quality. In testing, several models that
looked "broken" on MLX turned out to be **runtime bugs, not bad weights** — the identical weights
ran clean on GGUF/llama.cpp:

- **GLM-4.7-Flash crashed at 0% prompt processing on MLX.** Its MLA/latent-KV attention expects a
  plain-array KV cache, but LM Studio's MLX "KV Cache Quantization" setting returns a tuple
  instead, which the attention math can't handle — it even escalated to a full **macOS kernel
  panic** once. Same architectural gap hits DeepSeek V3 and Kimi K2.5 on MLX.
- **The Opus-reasoning distill had multi-turn tool-calling degradation and OOM crashes on MLX** —
  clean on GGUF with the identical weights.
- **MTP (Multi-Token Prediction) speculative decoding — ~1.4–2.2× faster generation — only works
  on Unsloth's patched llama.cpp.** It doesn't accelerate on MLX at all.

To be clear: **this isn't "MLX is bad."** MLX genuinely wins on raw decode speed and is a fine
choice for single-model chat. The finding is narrower: for agentic work — long contexts, big tool
results in the prompt, format-sensitive tool-calling — GGUF/llama.cpp was the more mature, reliable
runtime here. If MLX already works for you, there's no need to switch.

### Why Unsloth Studio, not Ollama?

Ollama also serves local GGUF models, so this is a fair follow-up. Short version: Unsloth trades
some integration convenience for a more capable engine, better quant quality, and fresher model
availability.

- **Engine: MTP speculative decoding.** Unsloth Studio's patched `llama.cpp` supports MTP
  (Multi-Token Prediction) — a ~1.4–2.2× generation speedup on models with an MTP head. Ollama's
  own engine doesn't expose this; mainline llama.cpp features often land in Ollama later, if at all.
- **Quant quality.** Unsloth's `UD-...` ("Dynamic") quants selectively keep more bits on sensitive
  layers instead of uniform quantization, measurably preserving quality better than a naive quant
  at the same file size. Ollama's library serves whatever quant got uploaded — usually a standard
  quant with no equivalent quality-preservation step.
- **Model freshness.** Unsloth typically ships GGUFs same-day for new open-weight model releases.
  Ollama's library depends on the community/Ollama team re-packaging models into Ollama's format,
  often lagging days to weeks.
- **Config ergonomics.** Context window, KV-cache quantization, chat-template kwargs, reasoning
  toggle — all plain CLI flags on `unsloth-serve`. Ollama needs env vars edited inside a
  version-pinned Homebrew plist file for something as basic as context length — breaks on every
  Ollama version bump.

**Where Ollama wins:** out-of-the-box integration. `ollama launch claude/opencode/codex/copilot` is
a one-liner, and it ships a native VS Code extension. This setup needed custom tooling
(`unsloth-serve`, `copilot-local`, the VS Code Custom Endpoint config) to get the same reach —
that's a real trade-off, not free.

---

Questions → open a GitHub issue. Background & field notes: `../docs/`, `../METHODOLOGY.md`, `../REPLICATION.md`.
