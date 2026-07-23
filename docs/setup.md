# Set up a local server

To reproduce the benchmark you need one thing: an **OpenAI-compatible endpoint on `localhost:8888`** serving an open-weight GGUF model. This repo ships the exact stack used for the runs, but any compatible local server works.

## The stack

- **[Unsloth Studio](https://unsloth.ai)** — a patched `llama.cpp` that serves GGUF models with MTP (multi-token-prediction) speculative decoding, on `127.0.0.1:8888`.
- **`unsloth-serve`** — a small launcher that starts one model at a time with tuned flags (36 GB holds one model).
- **A client** — [OpenCode](https://opencode.ai) (the agent client the benchmark drives), or VS Code's Copilot Chat via a custom BYOK endpoint.

## Quick start

```bash
git clone https://github.com/DresvyanskiyDenis/local-llm-coding-bench.git
cd local-llm-coding-bench/setup
./install.sh                 # interactive — answers y to each step, idempotent
```

Then, in a new terminal:

```bash
unsloth-serve ornith         # serve the #1 model on :8888 — wait for "model loaded"
```

The installer is idempotent (it skips whatever's already present) and lets you tick which models to download. Start with **`ornith`** (~22 GB) — you don't need the whole fleet.

## Full instructions

| Guide | For |
|-------|-----|
| [`setup/INSTALL.md`](https://github.com/DresvyanskiyDenis/local-llm-coding-bench/blob/main/setup/INSTALL.md) | The complete manual walkthrough — every command, run by hand, with a "check first" before each. |
| [`setup/README.md`](https://github.com/DresvyanskiyDenis/local-llm-coding-bench/blob/main/setup/README.md) | The setup bundle overview: automated vs manual install, the model fleet, what gets installed. |
| [`setup/UNSLOTH-CHEATSHEET.md`](https://github.com/DresvyanskiyDenis/local-llm-coding-bench/blob/main/setup/UNSLOTH-CHEATSHEET.md) | Unsloth Studio commands, flags, health checks, and troubleshooting. |
| [Local-LLM setup guide (deep dive)](local-llm-setup-guide.md) | Background: why GGUF/Unsloth, config ergonomics, the whole picture. |

## Behind a corporate proxy?

If your machine sits behind a TLS-intercepting proxy, model downloads (`hf download`) may fail with `certificate verify failed`. First `hf auth login` with a free HuggingFace token; if it still fails, point the downloader at your corporate CA bundle — see the "Known problems" section of [`setup/INSTALL.md`](https://github.com/DresvyanskiyDenis/local-llm-coding-bench/blob/main/setup/INSTALL.md).

Once `curl http://127.0.0.1:8888/v1/models` returns a model, head to **[Reproduce the benchmark](replication.md)**.
