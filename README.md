# local-llm-coding-bench

**An open, reproducible benchmark of local open-weight coding models running fully on-device on Apple Silicon (M-series) Macs** — scored across four suites: coding, code-review, surgical-edit, and free-text.

> This benchmark grew out of internal work at Liebherr evaluating local open-weight coding models on Apple Silicon Macs. It has been generalized and stripped of internal details for public replication.

📖 **[Read the documentation site →](https://dresvyanskiydenis.github.io/local-llm-coding-bench/)**

---

## Results teaser

Top 3 for **"a local agentic-coding driver in OpenCode"** (composite of correctness, tool reliability, edit precision, review recall, prose, and speed):

| # | Model | Quant | Composite | One line |
|---|-------|-------|:---------:|----------|
| 🥇 1 | Ornith-1.0 35B (MoE 35B-A3B) | Q4_K_M | **88.3** | No weak axis: near-top coding, best prose, fast. |
| 🥈 2 | Gemma-4 26B-A4B-it (MoE 26B-A4B) | Q4 / Q5 | **87.1** | Fastest decode + cleanest tool-calls. |
| 🥉 3 | Qwopus3.6 Coder MTP (MoE 35B-A3B) | Q5_K_M | **87.0** | Best pure coder; clean tools, MTP-fast. |

**Full 9-model ranking, per-suite breakdown, and the exact composite weighting → [LEADERBOARD.md](docs/leaderboard.md).** Method and honest gaps → [METHODOLOGY.md](docs/methodology.md).

---

## Key facts

- **9 working models** benchmarked (both Q4 and Q5 quants where they exist).
- **One machine:** MacBook Pro **M4 Max, 36 GB** unified memory — a real laptop, not a cluster.
- **~450 graded test units** across **4 suites** (10 tasks × 3 repetitions), plus a clean speed probe.
- **Fully local:** no code ever leaves the machine — no cloud API, no per-token cost.
- Driven through the **real stack**: an OpenAI-compatible local server + an OpenCode agent client.

---

## The four suites

| Suite | What it measures | Grading |
|-------|------------------|---------|
| **A — Coding** | Implement from a spec/stub in a repo | Hidden `pytest`, objective |
| **B — Review** | Find planted bugs, avoid hallucinating | Recall + precision vs a key |
| **C — Surgical edit** | Apply valid review fixes, ignore a noise comment | Hidden `pytest` + diff discipline |
| **D — Text** | Summarize + design/brainstorm | Single offline judge, rubric |

---

## Round 2 (in progress) — two lanes, external benchmarks

Round 1 measured one thing: the model driven through OpenCode — agentic, tool-using, multi-turn.
Round 2 adds a second, deliberately separate measurement rather than blending it into the first.

- **Lane 1 — in-harness** (round 1's A/B/C/D suites, now being expanded by bug/noise/context
  kind). Still runs through OpenCode. Measures the model **plus** the harness — tool-call
  formatting, context handling, and compaction behaviour all count.
- **Lane 2 — external** ([BigCodeBench Hard](https://github.com/bigcode-project/bigcodebench),
  [IFEval](https://arxiv.org/abs/2311.07911)): single-turn, straight to
  `/v1/chat/completions`, no agent, no tools. Measures the model alone, graded by verifiers
  vendored **unmodified** from their upstream projects — code nobody in this repo wrote.

A model can be strong in one lane and weak in the other; that gap is reported as a finding, not
explained away. Both external benchmarks land as **new axes reported alongside** the existing
composite — the composite formula itself is unchanged this round. BigCodeBench Hard here runs
local with relaxed dependency pins (the official path is a Docker image with no arm64 manifest, or
a remote Gradio executor that uploads solutions to a third party) — 148/148 hard tasks resolve
locally with 0 blocked, but the resulting `pass@1` is a **within-fleet** number, not comparable to
the public BigCodeBench leaderboard.

Full method: [`docs/methodology.md`](docs/methodology.md) §6. Live build/run status:
[`eval/ROUND2_STATUS.md`](eval/ROUND2_STATUS.md). Per-benchmark setup and repro commands:
[`eval/external/ifeval/README.md`](eval/external/ifeval/README.md),
[`eval/external/bigcodebench/README.md`](eval/external/bigcodebench/README.md).

---

## Repo layout

```
local-llm-coding-bench/
├── LEADERBOARD.md      ← full ranking + per-suite breakdown (start here)
├── METHODOLOGY.md      ← method, task set, known gaps
├── eval/
│   ├── harness/        ← resumable orchestrator, speed probe, graders, driver
│   ├── tasks/          ← the self-contained A/B/C/D task dirs
│   ├── external/       ← round-2 external lane: BigCodeBench Hard + IFEval adapters (vendored, unmodified graders)
│   └── results/        ← raw per-unit JSON + append-only manifest
├── bench/              ← lightweight smoke test for a serving endpoint
├── setup/              ← stand up the identical local serving stack on your Mac
└── docs/               ← setup guide and supporting notes
```

---

## Quickstart

1. **Stand up a local server.** Follow **[setup/](setup/README.md)** to install a patched
   `llama.cpp`-based Studio + launcher and serve an open-weight GGUF on `localhost:8888`.
2. **Reproduce the benchmark.** See **[REPLICATION.md](docs/replication.md)** for the full path —
   configs, task dirs, and the resumable `eval/harness/orchestrate.py` engine (`uv run … --resume`).
3. **Sanity-check the endpoint** any time with `uv run bench/smoke_test.py`.

---

## ⚠️ On non-determinism

**LLMs are stochastic.** Re-running this benchmark will **not** reproduce identical scores —
sampling, MTP acceptance, and serving nondeterminism all move the numbers run to run. What it
**should** reproduce is the **magnitude** of each score and the **broad ranking**: a model near
the top here should land near the top for you, and a 30% malformed-tool rate should still read as
a liability, not a rounding error. Treat single-decimal composite gaps as noise; treat suite-level
and rank-level differences as signal.

---

## Requirements

- **Apple Silicon** Mac (M1–M4), **≥ 32 GB** unified memory, macOS.
- **`uv`** + Python ≥ 3.11 (all harness scripts are PEP-723 inline-script style, run via `uv run`).
- A local **OpenAI-compatible** endpoint on `:8888` (the [setup/](setup/README.md) stack provides one).

## License

[MIT](LICENSE).
