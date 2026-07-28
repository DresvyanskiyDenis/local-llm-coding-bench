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

- **Lane 1 — in-harness** (round 1's A/B/C/D suites, expanded from 10 tasks to 31). Still runs
  through OpenCode. Measures the model **plus** the harness — tool-call formatting, context
  handling, and compaction behaviour all count.
- **Lane 2 — external** ([BigCodeBench Hard](https://github.com/bigcode-project/bigcodebench),
  [IFEval](https://arxiv.org/abs/2311.07911)): single-turn, straight to
  `/v1/chat/completions`, no agent, no tools. Measures the model alone, graded by verifiers
  vendored **unmodified** from their upstream projects — code nobody in this repo wrote.

**Ten BigCodeBench-Hard tasks run in both lanes.** That is the point of the pairing, not a
duplication: measuring a model on BigCodeBench in a separate lane mostly reproduces what the public
leaderboard already says, so the same upstream tasks are wrapped as in-harness tasks `A5`–`A14`
(`eval/tasks/A_coding/BCB_PAIRING.json` records the upstream ids) and the **difference between the
two lanes isolates the harness contribution**. A model can be strong in one lane and weak in the
other; that gap is the finding.

Round 1's `A_coding` is why. It saturated at 0.883–0.994 pass-rate — every config at the ceiling,
separating nothing — and inventing harder hand-written tasks would have been guessing where the
ceiling is.

Both external benchmarks land as **new axes reported alongside** the composite, unweighted, until
there is evidence of correlation. **The composite's internal weights did change this round**
(`tool_malformed` 0.25→0.10, `B_recall` +0.10, `C_edit` +0.05; methodology §6.11) — both weightings
stay computable on every row, and the round-1 weighting still reproduces the published leaderboard
9/9, which is what licenses reusing round 1's units instead of re-running them.

Every reported number carries the denominator it was measured over: a composite states how many of
the selected set's tasks it actually covers, and an external axis renders as `0.300 ‡10/148` when it
is a slice rather than a full-set score — with a `⚠` when the slice is contaminated as well as
partial (methodology §6.12).

BigCodeBench Hard here runs local with relaxed dependency pins (the official path is a Docker image
with no arm64 manifest, or a remote Gradio executor that uploads solutions to a third party) —
148/148 hard tasks resolve locally with 0 blocked, but the resulting `pass@1` is a **within-fleet**
number, not comparable to the public BigCodeBench leaderboard.

Scope of the round-2 run: **855 units pending of 1305 planned** (15 configs × 31 tasks × reps).
The 450 round-1 units are skipped mechanically — `process_config()` filters to units whose result
file does not exist — and that reuse is licensed by Phase 3's gate, which proves the graders
re-grade round-1 fixtures byte-identically.

Full method: [`docs/methodology.md`](docs/methodology.md) §6. Live build/run status:
[`eval/ROUND2_STATUS.md`](eval/ROUND2_STATUS.md). Per-benchmark setup and repro commands:
[`eval/external/ifeval/README.md`](eval/external/ifeval/README.md),
[`eval/external/bigcodebench/README.md`](eval/external/bigcodebench/README.md).

---

## Repo layout

```
local-llm-coding-bench/
├── eval/
│   ├── harness/        ← resumable orchestrator, speed probe, graders, driver
│   ├── tasks/          ← the self-contained A/B/C/D task dirs
│   ├── external/       ← round-2 external lane: BigCodeBench Hard + IFEval adapters (vendored, unmodified graders)
│   └── results/        ← raw per-unit JSON + append-only manifest
├── bench/              ← lightweight smoke test for a serving endpoint
├── setup/              ← stand up the identical local serving stack on your Mac
└── docs/               ← the published documentation site — the two headline documents live here
    ├── leaderboard.md  ← full ranking + per-suite breakdown (start here)
    ├── methodology.md  ← method, task set, known gaps
    ├── replication.md  ← how to re-run the benchmark end-to-end
    └── setup.md        ← setup guide and supporting notes
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
