# local-llm-coding-bench

**An open, reproducible benchmark of local open-weight coding models running fully on-device on Apple Silicon (M-series) Macs** — scored across four suites: coding, code-review, surgical-edit, and free-text.

!!! quote "Origin"
    This benchmark grew out of internal work at Liebherr evaluating local open-weight coding models on Apple Silicon Macs. It has been generalized and stripped of internal details for public replication.

## Results at a glance

Top 3 for **"a local agentic-coding driver in OpenCode"** (composite of correctness, tool reliability, edit precision, review recall, prose, and speed):

| # | Model | Quant | Composite | One line |
|---|-------|-------|:---------:|----------|
| 🥇 1 | Ornith-1.0 35B (MoE 35B-A3B) | Q4_K_M | **88.3** | No weak axis: near-top coding, best prose, fast. |
| 🥈 2 | Gemma-4 26B-A4B-it (MoE 26B-A4B) | Q4 / Q5 | **87.1** | Fastest decode + cleanest tool-calls. |
| 🥉 3 | Qwopus3.6 Coder MTP (MoE 35B-A3B) | Q5_K_M | **87.0** | Best pure coder; clean tools, MTP-fast. |

**Full 9-model ranking, per-suite breakdown, and the exact composite weighting → [Leaderboard](leaderboard.md).** There's also an [offline sortable HTML view](leaderboard.html).

## Key facts

- **9 working models** benchmarked (both Q4 and Q5 quants where they exist).
- **One machine:** MacBook Pro **M4 Max, 36 GB** unified memory — a real laptop, not a cluster.
- **~450 graded test units** across **4 suites** — the **round-1 published set**, 10 tasks × 3 repetitions — plus a clean speed probe.
- **Fully local:** no code ever leaves the machine — no cloud API, no per-token cost.
- Driven through the **real stack**: an OpenAI-compatible local server + an OpenCode agent client.

## The four suites

| Suite | What it measures | Grading |
|-------|------------------|---------|
| **A — Coding** | Implement from a spec/stub in a repo | Hidden `pytest`, objective |
| **B — Review** | Find planted bugs, avoid hallucinating | Recall + precision vs a key |
| **C — Surgical edit** | Apply valid review fixes, ignore a noise comment | Hidden `pytest` + diff discipline |
| **D — Text** | Summarize + design/brainstorm | Single offline judge, rubric |

## Round 2 (in progress) — two lanes, external benchmarks

Everything above is round 1. Round 1 measured one thing: the model driven through OpenCode — agentic, tool-using, multi-turn. Round 2 adds a second, deliberately separate measurement rather than blending it into the first.

- **Lane 1 — in-harness:** round 1's A/B/C/D suites, expanded from 10 tasks to **31**, still driven through OpenCode. Measures the model **plus** the harness — tool-call formatting, context handling, and compaction behaviour all count.
- **Lane 2 — external:** [BigCodeBench Hard](https://github.com/bigcode-project/bigcodebench) and [IFEval](https://arxiv.org/abs/2311.07911), single-turn straight to `/v1/chat/completions`, no agent and no tools, graded by verifiers vendored **unmodified** from upstream. Measures the model alone.

**Ten BigCodeBench-Hard tasks run in both lanes** — wrapped as in-harness tasks `A5`–`A14` — so the difference between the two lanes isolates the harness contribution. Round 1's `A_coding` is why: it saturated at 0.883–0.994 pass-rate and separated nothing.

Both external benchmarks land as **new axes reported alongside** the composite, unweighted, until there is evidence of correlation. **The composite's internal weights did change this round** (`tool_malformed` 0.25→0.10, `B_recall` +0.10, `C_edit` +0.05) — both weightings stay computable on every row, and the round-1 weighting still reproduces the published leaderboard 9/9, which is what licenses reusing round 1's units instead of re-running them.

Every reported number carries the denominator it was measured over: an external axis renders as `0.300 ‡10/148` when it is a slice rather than a full-set score, with a `⚠` when the slice is contaminated as well as partial.

Scope of the round-2 run: **855 units pending of 1305 planned** (15 configs × 31 tasks × reps). The 450 round-1 units are skipped mechanically rather than re-run.

Full method → [Methodology §6](methodology.md). Live build/run status → [`eval/ROUND2_STATUS.md`](https://github.com/DresvyanskiyDenis/local-llm-coding-bench/blob/main/eval/ROUND2_STATUS.md).

## Start here

<div class="grid cards" markdown>

- :material-server-network: **[Set up a local server](setup.md)** — stand up the identical serving stack on your Mac and serve a GGUF on `localhost:8888`.
- :material-play-circle: **[Reproduce the benchmark](replication.md)** — configs, task dirs, and the resumable orchestrator, step by step.
- :material-trophy: **[Read the leaderboard](leaderboard.md)** — full ranking, per-suite numbers, and the composite formula.
- :material-microscope: **[Understand the method](methodology.md)** — task design, grading, and the honest gaps.

</div>

## :material-alert: On non-determinism

**LLMs are stochastic.** Re-running this benchmark will **not** reproduce identical scores — sampling, MTP acceptance, and serving nondeterminism all move the numbers run to run. What it **should** reproduce is the **magnitude** of each score and the **broad ranking**: a model near the top here should land near the top for you. Treat single-decimal composite gaps as noise; treat suite-level and rank-level differences as signal.

## Requirements

- **Apple Silicon** Mac (M1–M4), **≥ 32 GB** unified memory, macOS.
- **`uv`** + Python ≥ 3.11 (harness scripts are PEP-723 inline-script style, run via `uv run`).
- A local **OpenAI-compatible** endpoint on `:8888` (the [setup stack](setup.md) provides one).

Licensed [MIT](https://github.com/DresvyanskiyDenis/local-llm-coding-bench/blob/main/LICENSE).
