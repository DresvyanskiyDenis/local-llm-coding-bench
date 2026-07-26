# Benchmark Methodology — Local-LLM Coding Bench

How this benchmark is designed, run, and scored. Grounded in the harness contract
([`eval/harness/CONTRACT.md`](https://github.com/DresvyanskiyDenis/local-llm-coding-bench/blob/main/eval/harness/CONTRACT.md)), the master plan
([`eval/PLAN.md`](https://github.com/DresvyanskiyDenis/local-llm-coding-bench/blob/main/eval/PLAN.md)), the actual task tree under `eval/tasks/`, the graders under
`eval/harness/graders/`, and the produced results
([`eval/results/METRICS_ROLLUP.md`](https://github.com/DresvyanskiyDenis/local-llm-coding-bench/blob/main/eval/results/METRICS_ROLLUP.md),
[`eval/results/LEADERBOARD.md`](https://github.com/DresvyanskiyDenis/local-llm-coding-bench/blob/main/eval/results/LEADERBOARD.md)).

## Purpose

Answer one real decision, not a synthetic score: **which local model + quant is the best
day-to-day agentic coding driver on a 36 GB MacBook Pro M4 Max, and what does each cost in speed
and quality?** Everything is tested on the real stack — Unsloth Studio serving on
`127.0.0.1:8888` (one model at a time) driven by the OpenCode agent client — with a controlled
raw-endpoint speed probe bolted on for clean throughput numbers. Realism over synthetic purity:
models are graded on the same client, tasks, tools, and graders a user would actually hit.

---

## 1. The four suites

Every task is a self-contained directory `eval/tasks/<suite>/<task-id>/` containing `PROMPT.md`
(the only instruction the model sees), a starting `repo/` (or `source/` for text), a hidden
`grade/` never shown to the model, and a `meta.json` declaring the grader. Domain is locked to
**Python, self-contained, deterministically gradeable — no live Spark/Databricks**. Every task
is kept small (<~30K context tokens) so per-config context caps never bite.

### A_coding — from-scratch implementation (objective, functional tests)
Model implements a spec/stub in `repo/src/solution.py`; a hidden `pytest` suite decides the
score. Measures whether the model can write correct code from a specification. 4 tasks:
- `A1_events_sessionize` — sessionize a user-events log by inactivity gap (pandas)
- `A2_record_validation` — a data-validation function
- `A3_lru_cache` — a small pure-Python algorithm (LRU cache)
- `A4_int_to_roman` — HumanEval+-style classic function with a strong hidden test set (for
  public-benchmark comparability)

### B_review — code review (semi-objective, planted-bug recall + precision)
`repo/` contains a module with a **known planted-bug key**; the model must review it and list
bugs in a mandated machine-parseable format. Measures recall (found/planted) and precision
(real vs hallucinated findings). 2 tasks:
- `B1_customer_cleaning` — customer-record cleaning pipeline
- `B2_order_pricing` — order-pricing module

### C_edit — surgical edits (objective, functional tests + discipline)
`repo/` holds working-ish code plus a `REVIEW.md` of review comments, **exactly one of which is
a deliberate noise/wrong comment**. The model applies the valid fixes and must NOT act on the
noise. Measures correctness (hidden pytest) AND surgical discipline (did it touch only what was
asked, did it correctly ignore the noise). 2 tasks:
- `C1_inventory` — apply valid fixes to inventory helpers, ignore the noise comment
- `C2_text_utils` — same pattern on text-utility code

### D_text — summarize / brainstorm (subjective, single offline judge)
Prose tasks driven through the same agent, scored offline by a single judge (Opus) 0–10 to kill
judge variance. 2 tasks:
- `D1_summarize_mtp` — summarize a technical doc on prefill/decode + speculative decoding/MTP;
  scored on key-point recall (`grade/key_points.json`) plus a rubric
- `D2_dedup_approaches` — "give 3 approaches to cross-schema record linkage, with tradeoffs";
  scored on a rubric only

**Total: 10 tasks** — 4 A + 2 B + 2 C + 2 D.

Alongside the quality scores, each unit also records tool-call validity (share malformed),
agentic turns-to-done, termination reason, wall-clock, TTFT (cold vs warm), think:answer token
ratio, and peak RAM.

---

## 2. Test-unit math (~450 graded units)

The unit of work is a single `(model, quant, suite, task, rep)` tuple, written as one atomic
result JSON `eval/results/<model>__<quant>__<suite>__<task>__rep<N>.json`.

```
tasks                        = 10   (4 A_coding + 2 B_review + 2 C_edit + 2 D_text)
working models               =  9   (qwen27 broke on smoke → 0 units, excluded)
model × quant configs        = 15   (see breakdown below)
reps per (config, task)      =  3   (3× everywhere it works, for variance / CIs)

graded units = tasks × configs × reps = 10 × 15 × 3 = 450
```

The 15 configs come from the 9 working models — quant A/B (Q4 vs Q5) wherever both quants exist,
single quant otherwise:

| Model | Configs | Quants |
|---|--:|---|
| opus | 2 | q4, q5 |
| qwen | 2 | q4, q5 |
| glm | 2 | q4, q5 |
| gemma | 2 | q4, q5 |
| northmini | 2 | q4, q5 |
| katdev | 2 | q4, iq4 |
| qwopus | 1 | q5 (single) |
| ornith | 1 | q4 (single) |
| gpt-oss | 1 | mxfp4 (single, native) |
| **total** | **15** | |

`9 models → 15 configs × 10 tasks × 3 reps = 450 units`. Each config therefore contributes
`10 × 3 = 30` units. All 450 unit JSONs parsed cleanly (0 unparseable). A 10th model, `qwen27`,
was rostered but smoke-failed both quants (serve/template issue) → 0 units, excluded from every
aggregate; its speed probe was still attempted per the broken-policy.

---

## 3. Grading — per suite

Each grader is a standalone `uv run` CLI
(`--task <taskdir> --run <rundir> --out <path.json>`) that reads the model's produced working
copy and the hidden `grade/` dir, and writes a JSON verdict. Graders exit 0 even on a failing
grade (a failed task is data, not a script error); non-zero only on grader malfunction.

### A_coding → `pytest_grader.py` (functional tests)
Copies the task's `grade/test_*.py` into a sibling of the model's `repo/` (never into `repo/`
itself, so the diff grader still sees only the model's edits), points `PYTHONPATH` at `repo/`,
and runs `pytest --junitxml` parsed with stdlib XML (no plugin dependency). Verdict reports
`passed / failed / errors / total`, a **`pass_rate`** (the headline number), and a
`failure_class` (`no_file | import_error | syntax_error | timeout | assertion | null`). Tests
are deterministic (fixed seeds, no network, no clock) and were run against author reference
solutions so truth is known-green.

### B_review → `review_grader.py` (planted-bug key match)
Parses the model's `answer.txt` for a single fenced ```json block containing a list of
`{file, line, description}` objects (the format both B prompts mandate). Each finding is matched
against `grade/key.json` (`{bugs:[{id, location:{file,line_start,line_end}, synonyms, severity}]}`):
a **confident match** requires location overlap (same file, line inside the planted range) AND a
description matching a synonym / id / canonical description. A finding matching only one signal
is recorded as **ambiguous** (saved for Opus adjudication, never guessed); anything else counts
toward hallucinated or missed. Verdict reports **recall** (found/planted) and **precision**
(real/(real+hallucinated)), plus matched/missed ids.

### C_edit → `diff_pytest` = `pytest_grader.py` + `diff_grader.py` (merged)
Two graders run and merge. `pytest_grader` re-runs the hidden test suite for correctness (same
as A). `diff_grader` diffs the original task `repo/` against the model's edited `repo/` (difflib
— repos are plain trees, not git) and reports `files_touched`, `lines_added/removed`,
`touched_expected_only` (checked against `meta.json`'s `entrypoint`), **`noise_comment_acted_on`**
(checked against `grade/noise.json` — both C tasks use the "required pattern must survive" kind,
so acting-on == correct code went missing), and a heuristic **`surgical_score`** (1.0 minus
penalties for unexpected files and for changed lines beyond a 15-line free allowance, minus 0.3
if the noise comment was wrongly followed).

### D_text → `judge` (single offline judge, Opus, 0–10)
The driver only saves the model's answer; **no automated grader**. In Stage 3 a single judge
(Opus) scores every model's answer against `grade/rubric.md` (and `grade/key_points.json` for
the summary task) on a 0–10 scale. One judge across all models eliminates judge variance.
Results land in `DTEXT_JUDGED.{json,md}`.

### Normalization
Per-suite scores are put on a common scale before combining: A/C report pytest **pass-rate**
(0–1); B reports **recall** (0–1); D reports the judge mean **/10**; tool reliability is
`1 − malformed%`; decode throughput is normalized to the fleet max (137 t/s). RAM is treated as
a hard constraint, not a scored axis.

---

## 4. Composite ranking

Per-suite scores combine into one auditable composite under a single explicit weighting for the
question "a local agentic-coding driver in OpenCode" (from `LEADERBOARD.md`):

```
Overall = 0.35·A_coding               (writes correct code)
        + 0.25·(1 − tool_malformed%)  (drives tools without malformed calls)
        + 0.15·C_edit                 (surgical-edit precision)
        + 0.10·B_recall               (planted-bug review)
        + 0.10·(D_text / 10)          (prose quality)
        + 0.05·(decode / 137)         (raw speed tiebreaker)
        → ×100
```

Rationale: for an agentic driver the two things that matter most are **correct code** (A, 35%)
and **clean tool-calling** (25%); surgical edits (C, 15%) come next; review recall and prose
(10% each) are secondary; raw decode speed is a 5% tiebreaker. Each model's **q4** quant is used
(single quant where only one was tested); decode normalized to the fleet-max 137 t/s. This
produced the headline ranking (ornith 88.3 → gemma 87.1 → qwopus 87.0 → opus 86.6 → … →
gpt-oss 77.1).

**"No weak axis"** is the property the composite rewards and the reason the top model wins: a
model with no low score on any dimension (coding, tools, edits, review, prose, speed) beats a
model that peaks on one axis but craters on another. Concretely, `qwen` has the best raw coding
+ prose yet a 28–32% malformed-tool tax drops it to 7th; `ornith` tops the table not by leading
any single axis outright but by being near-top on coding, best-tie on review recall, best on
prose, and acceptable on tools and speed — nothing drags it down. This is one weighting; sorting
by any single axis changes the winner (qwen leads raw coding, gemma leads speed, opus leads
balance), so the per-dimension winners are reported alongside the composite.

---

## 5. Fairness & controls

- **One machine, one model loaded at a time.** MacBook Pro M4 Max, 36 GB unified (weights
  realistically ≤ ~24 GB, leaving headroom for the OS + agent client + browser). Unsloth Studio
  serves exactly one model on `:8888`; the orchestrator unloads and verifies RAM release before
  serving the next config. Serving hazards are guarded (silent `:8889` rebind, zombie-parent 502
  after OOM, `--no-context-shift` freeze).
- **Identical prompts & tasks across all models.** The same task dirs and the same `PROMPT.md`
  feed every model via the same `opencode_driver.py`; the model sees only `PROMPT.md` + the
  starting `repo/`, never `grade/`.
- **Reasoning effort locked HIGH for every thinking model.** Each model is tested at its
  strongest, not its fastest; the driver forces thinking-on and records the effort knob and
  think-token count (metric #12). Reasoning-off models (katdev, qwopus, ornith) run non-thinking
  by design and record 0 think tokens.
- **3 reps everywhere it works**, for pass-rate variance / confidence intervals. A quant that
  passes 1/3 is not "keep". The only exception is the **broken policy**: a config that won't
  load, calls no tools, or emits garbage on smoke is marked `broken` and skipped for the 3×
  quality depth (speed probe still attempted).
- **Clean speed probe separate from agent wall-clock.** Throughput (prefill/decode/TTFT) is
  measured on the raw endpoint over escalating context (2K/8K/24K/48K; the planned 80K point was
  skipped), 3× per config, so speed comparability does not depend on OpenCode base-prompt size
  (which varied run-to-run with flaky MCP reachability, and was never apples-to-apples in the
  agent wall-clock).
- **Resumability & auditability.** Every unit is an atomic JSON (temp file + rename) plus an
  append-only `manifest.jsonl` line; the engine skips any unit whose file exists, so `--resume`
  is just re-running it. All raw model outputs (`transcript.json`, `answer.txt`, edited `repo/`)
  are saved so grading is re-runnable without re-inferring.

### Cross-cutting quant finding
Most models were tested at both **q4 and q5**. A consistent result: **Q4 ≥ Q5 on coding** across
the board — equal-or-better pass-rate at lower RAM — so Q4 is the recommended default for coding.

### Honest limits (documented, not fabricated)
- **Harness-bug correction (2026-07-17):** an `opencode-log-sanitizer` plugin was rewriting the
  task prompt to the literal string `"redacted"` for the three night-3 models (katdev, qwopus,
  ornith), which had ranked them dead last. Plugin removed → clean re-run → they invert to
  top-of-fleet. The lesson baked into this methodology: validate the harness before writing off
  a model.
- **Not measured:** MTP speculative-decode acceptance rate (#3 — the probe never captured the
  timings; the field is null fleet-wide, do not infer it from decode t/s); the 80K probe point
  (skipped, curves are 4-point); quality degradation over long context (#10) and auto-compaction
  survival (#13) — all A/B/C/D tasks stay <30K ctx, below OpenCode's ~74K compaction trigger, so
  neither was exercised. These are task-set / probe-instrumentation gaps, stated as gaps rather
  than estimated.
- **`qwen27`** remains broken (serve/template, not the sanitizer): smoke-failed both quants →
  0 units, excluded from the ranking.

# Local-LLM Coding Benchmark — Leaderboard

Which local model + quant should you actually run as an **agentic coding driver** on a 36 GB Apple-silicon laptop? This is the consolidated answer from a 3-night benchmark: **450 graded units across 9 working models** (10 tasks × 3 reps over four suites), driven through the real stack — a local OpenAI-compatible server + an OpenCode agent client — plus a separate clean speed probe.

> An offline, sortable HTML view of this leaderboard (verdict cards + metric glossary + methodology timeline) ships alongside this file: open [`leaderboard.html`](leaderboard.html) in a browser.
>
> Full method, task set, and honest gaps: **[METHODOLOGY.md](methodology.md)**. Authoritative computed sources: [`eval/results/LEADERBOARD.md`](https://github.com/DresvyanskiyDenis/local-llm-coding-bench/blob/main/eval/results/LEADERBOARD.md) and [`eval/results/METRICS_ROLLUP.md`](https://github.com/DresvyanskiyDenis/local-llm-coding-bench/blob/main/eval/results/METRICS_ROLLUP.md).

## Composite ranking

There is no single "best" without saying *best at what*, so the headline ranking uses one explicit, auditable weighting for **"a local agentic-coding driver in OpenCode"**:

```
Overall = 0.35·A_coding + 0.25·(1 − tool_malformed%) + 0.15·C_edit
        + 0.10·B_recall + 0.10·(D_text/10) + 0.05·(decode/137)      → ×100
```

Rationale: for an agentic driver the two things that matter most are **does it write correct code** (A, 35%) and **does it drive tools without malformed calls** (tools, 25%); surgical-edit precision (C, 15%) is next; planted-bug review (B) and prose (D) are secondary (10% each); raw speed is a 5% tiebreaker. RAM is a constraint, not scored. The composite uses the **q4** quant (or the model's single quant); decode is normalized to the fleet max of 137 t/s.

| # | Key | Model | Quant | Composite | Role (one line) |
|---|-----|-------|-------|:---------:|-----------------|
| **1** | `ornith` ⊘ | Ornith-1.0 35B MTP-graft (MoE 35B-A3B) | Q4_K_M | **88.3** | No weak axis: near-top coding, best prose, best-tie review recall, fast. |
| 2 | `gemma` | Gemma-4 26B-A4B-it (MoE 26B-A4B) | Q4 / Q5 | 87.1 | Fastest decode + cleanest tool-calls; docked for A-suite timeouts. |
| 3 | `qwopus` ⊘ | Qwopus3.6 Coder MTP (MoE 35B-A3B) | Q5_K_M | 87.0 | Best coding in the fleet; clean tools, MTP-fast, non-thinking. |
| 4 | `opus` | Qwen3.6-35B Opus-4.6 distill (MoE 35B-A3B) | Q4 / Q5 | 86.6 | Safest, most-balanced daily driver; fastest genuine completion. |
| 5 | `glm` | GLM-4.7-Flash (MoE 30B-A3B) | Q4 / Q5 | 84.9 | Best surgical edits (C 0.909 q5); clean tools, mid speed. |
| 6 | `northmini` ⊘ | North-Mini-Code 1.0 | Q4 / Q5 | 83.7 | Strong non-thinking all-rounder; tool reliability (18–19%) is the wart. |
| 7 | `qwen` | Qwen3.6-35B-A3B MTP (MoE 35B-A3B) | Q4 / Q5 | 83.0 | Best raw coding + prose, but a 28–32% malformed-tool tax sinks it. |
| 8 | `katdev` ⊘ | KAT-Dev 32B (DENSE 32B) | Q4 / IQ4 | 82.2 | Correct + cleanest tools, but dense → slow (~13 t/s). |
| 9 | `gpt-oss` | gpt-oss-20b (20B) | MXFP4 | 77.1 | Tiny RAM (13.6 GB); slow; weakest review recall (0.11). |

⊘ = **non-thinking** (reasoning disabled at serve). This is **one** weighting — sort by any single axis and the winner changes: `qwen` leads raw coding + prose, `gemma` leads speed, `opus` leads balance.

## Per-suite breakdown

Numbers are `q4 / q5` unless noted (`katdev` shown `q4 / iq4`; single-quant models show one value). **A / C / B** are pass-rate or recall; **D_text** is the 0–10 offline-judge mean; **Tools** = share of tool-calls that were malformed (lower is better); **Decode** = probe throughput (t/s); **RAM** = peak GB.

| Key | A_coding | C_edit | B_review recall | D_text | Tools malformed | Decode t/s | RAM GB |
|-----|:--------:|:------:|:---------------:|:------:|:---------------:|:----------:|:------:|
| `ornith` ⊘ | 0.987 | 0.863 | **0.556** | **9.83** | 9% | 74 | 25.3 |
| `gemma` | 0.911 / 0.911 | 0.863 / 0.863 | 0.333 / 0.445 | 9.67 | **3% / 2%** | **137 / 92** | 27.5 / 24.1 |
| `qwopus` ⊘ | **0.994** | 0.863 | 0.389 | 8.83 | 3% | 63 | 27.1 |
| `opus` | 0.976 / 0.923 | 0.863 / 0.818 | 0.445 / 0.611 | 8.67 | 5% / 3% | 72 / 68 | 24.0 / 25.9 |
| `glm` | 0.916 / 0.880 | 0.879 / **0.909** | 0.445 / 0.445 | 8.83 | 3% / 4% | 58 / 65 | 24.7 / 26.8 |
| `northmini` ⊘ | 0.942 / 0.898 | 0.879 / 0.803 | **0.556** / 0.444 | 9.58 | 19% / 18% | 58 / 55 | 26.1 / 24.4 |
| `qwen` | 0.991 / 0.970 | **0.894** / 0.863 | 0.500 / 0.556 | 9.75 | 32% / 28% | 87 / 93 | 24.9 / 27.6 |
| `katdev` ⊘ | 0.885 / 0.946 | 0.863 | 0.333 / 0.278 | 9.08 | 2% / 5% | 13 / 14 | 27.7 / 27.8 |
| `gpt-oss` | 0.883 | 0.863 | 0.111 | 8.83 | 11% | 30 | **13.6** |

### Per-dimension winners

- **Coding (A):** `qwopus` (0.994) → `qwen` (0.991) → `ornith` (0.987) → `katdev`-iq4 (0.946) → `northmini` (0.942)
- **Surgical edit (C):** `glm`-q5 (0.909) → `qwen`-q4 (0.894) → `northmini`/`glm`-q4 (0.879); everyone else clusters at 0.863
- **Review recall (B):** `ornith` & `northmini`-q4 (0.556), `opus`-q5 (0.611) — still the fleet-wide weak axis (0.11–0.61)
- **Free-text (D):** `ornith` (9.83) → `qwen` (9.75) → `gemma` (9.67) → `northmini` (9.58) → `katdev` (9.08)
- **Tool reliability:** `gemma` (2–3%), `katdev` (2–5%), `qwopus` (3%), `glm` (3–4%), `opus` (3–5%) — `qwen`'s 28–32% is the standout liability
- **Speed (decode):** `gemma`-q4 (137) → `qwen`-q5 (93) → `gemma`-q5 (92) → `qwen`-q4 (87) → `ornith` (74)
- **RAM:** `gpt-oss` (13.6 GB) in a class of its own; everything else 24–28 GB

## Bottom line for daily use

- **Default driver:** `opus` (q4) — balanced, reliable tools, fastest genuine completion.
- **Max coding, non-thinking, clean tools:** `qwopus` (q5, A 0.994) or `ornith` (q4, A 0.987 + best prose).
- **Max coding/prose, will tolerate tool retries:** `qwen` (q4).
- **Best surgical edits:** `glm` (q5, C 0.909).
- **Tightest RAM budget:** `gpt-oss` (13.6 GB), accepting slow + weak review.
- **Prefer Q4 over Q5 for coding** across the board — cheaper RAM, equal-or-better quality.

## Notes

- **`qwen27`** was excluded (smoke-failed both quants, 0 units — a serve/template issue).
- Reasoning-off is not a handicap here: four of the top coders (`qwopus`, `ornith`, `northmini`, `katdev`) run non-thinking, and two of them top the coding and prose axes.
- Known measurement gaps (MTP acceptance rate, 80 K context probe point, long-context quality decay, auto-compaction survival) are documented in [METHODOLOGY.md](methodology.md) and [`eval/results/METRICS_ROLLUP.md`](https://github.com/DresvyanskiyDenis/local-llm-coding-bench/blob/main/eval/results/METRICS_ROLLUP.md).

*Benchmark hardware: MacBook Pro M4 Max, 36 GB unified memory. Composite computed on the q4 (or single) quant of each model.*

# REPLICATION — reproduce this benchmark from scratch

This is the step-by-step guide to re-run the local-LLM coding benchmark end to end: stand up a
local OpenAI-compatible server, smoke-test it, run the full resumable eval, aggregate the scores,
and compare against the published leaderboard.

Authoritative design docs, read alongside this guide:
- [`eval/PLAN.md`](https://github.com/DresvyanskiyDenis/local-llm-coding-bench/blob/main/eval/PLAN.md) — the master contract (why, config matrix, 13 metrics, resumability).
- [`eval/harness/CONTRACT.md`](https://github.com/DresvyanskiyDenis/local-llm-coding-bench/blob/main/eval/harness/CONTRACT.md) — the hard interfaces (task/grader/driver/result schemas).
- [`METHODOLOGY.md`](methodology.md) — the scoring method + honest gaps.
- [`LEADERBOARD.md`](leaderboard.md) — the published numbers you are reproducing.

Everything runs as PEP-723 inline-script style: `uv run <script>`. There is **no project venv** —
`uv` resolves each script's declared deps on the fly. Never use `pip`.

---

## 1. Hardware / OS prerequisites

| Requirement | Value used for the published run |
|---|---|
| Machine | Apple Silicon Mac (M1–M4). Reference: **MacBook Pro M4 Max** |
| Unified memory | **36 GB** (≥32 GB required — one model at a time must fit in ~24 GB of weights + KV) |
| OS | macOS (the harness shells out to `lsof`, `pgrep`, `vm_stat`, `ps`, `caffeinate`, `memory_pressure`) |
| Python | **≥ 3.11** (declared in every script's `# requires-python` header) |
| `uv` | required — runs every harness/bench/grader script. `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| Disk | ~170 GB free if downloading the full fleet of GGUFs; far less for a single model |
| `opencode` CLI | required to run the eval (the driver shells out to `opencode run` / `opencode export`) |

RAM budget rationale (PLAN §1): weights must fit ~24 GB, leaving ~4 GB for macOS + the OpenCode
client (~1.5 GB) + a browser. That is why only **one model is served at a time**.

> Note on the GPU wired limit: the serving stack raises `iogpu.wired_limit_mb` to `(RAM − 4 GB)`.
> The team installer does this as an opt-in `--with-system` step (a sudo LaunchAgent). Without it,
> the larger 24–28 GB models may not fully offload to the GPU.

---

## 2. Stand up a local OpenAI-compatible server

The benchmark drives whatever answers on **`http://127.0.0.1:8888/v1`** in OpenAI-compatible form.
Two paths:

### Path A (recommended) — the exact stack under test: Unsloth Studio + `unsloth-serve`

The `setup/` folder ships the full team installer (Unsloth Studio = patched `llama.cpp`, the
`~/bin/unsloth-serve` launcher, an OpenCode config, and the shell env with the API key).

```bash
cd setup/team-setup       # (or wherever setup/ places install.sh — see setup/README.md)
./install.sh              # interactive; answer y to each step
```

During install:
1. Log in to HuggingFace with a free token when prompted (this is what makes downloads work,
   even behind a corporate VPN).
2. Pick model(s) to download at the models prompt. To reproduce the #1 result start with
   `ornith` (~22 GB); you do **not** need all eight to begin.

Then, in a **new terminal** (so `~/.zshenv` loads the `PATH` + `UNSLOTH_STUDIO_API_KEY`):

```bash
unsloth-serve ornith      # serves the picked model on 127.0.0.1:8888; wait for "model loaded"
```

`unsloth-serve` accepts one of the 8 public fleet names:
`ornith | gemma | qwopus | opus | glm | northmini | qwen | gpt-oss` (default `qwen`). Serve exactly
one at a time — 36 GB holds one; stop it (Ctrl-C) before starting another.

> **Full-matrix caveat.** The published run tested most models at **both q4 and q5** (see
> `eval/harness/configs.json`, which references serve names like `qwen4`, `opus4`, `glm4`,
> `northmini4`, `gemma4`, plus the `katdev`/`qwen27` exotics). The *public* `unsloth-serve` ships
> one quant per model and 8 models only. To reproduce the entire q4↔q5 matrix you must add a
> `unsloth-serve` case for each quant variant (pointing at that quant's GGUF) whose label matches
> the `serve_name` in `configs.json`. To reproduce a **single model at its published quant**, the
> 8-model launcher is enough — trim `configs.json` to just that config (see §4).

### Path B — any other localhost:8888 OpenAI-compatible endpoint

Nothing in the harness is Unsloth-specific at the protocol level: it POSTs
`/v1/chat/completions` with `tools` and reads `choices[].message.tool_calls` + `timings`. Any
server that speaks that on `127.0.0.1:8888` (plain `llama-server`, LM Studio, etc.) works. If it
listens elsewhere, the smoke test takes `--base-url`, but `orchestrate.py`/`speed_probe.py`/the
driver hardcode `127.0.0.1:8888`, so serve there for a faithful run. Also register each model id in
`~/.config/opencode/opencode.json` under `provider.unsloth-studio.models` (the driver and the
dry-run check both read it) — the models declaring `"reasoning": true` are the ones the driver runs
at high effort (`opencode run --variant high`).

**API key:** every client reads `UNSLOTH_STUDIO_API_KEY`, falling back to the literal dev key
`sk-local-dummy-key`. Path A sets it in `~/.zshenv`. For Path B, either export it or pass
`--api-key` to the smoke test (the other scripts only read the env var).

---

## 3. Smoke test — confirm the endpoint answers and drives tools

Once a model is serving, verify tool-calling before spending hours on the full eval:

```bash
# human-readable table
uv run bench/smoke_test.py --model <opencode-model-id>

# machine-readable (what orchestrate.py runs internally)
uv run bench/smoke_test.py --model <opencode-model-id> --json

# repeat the 6-scenario suite N times
uv run bench/smoke_test.py --model <opencode-model-id> --rounds 3
```

Concrete example for the `ornith` model:

```bash
uv run bench/smoke_test.py --model tashfene/Ornith-1.0-35B-MTP-Q4_K_M-GGUF --json
```

Flags (verified against `bench/smoke_test.py`): `--base-url` (default
`http://127.0.0.1:8888/v1`), `--model` (default `unsloth/Qwen3.6-35B-A3B-MTP-GGUF`), `--api-key`
(default: `$UNSLOTH_STUDIO_API_KEY` → `sk-local-dummy-key`), `--json`, `--rounds N`.

The suite runs 6 scenarios (single call, nested-object args, multi-turn chain, parallel calls, a
no-tool control, long-context call). Read `overall tools:` — `pass` / `partial` / `fail`. A `fail`
here is exactly what `orchestrate.py` uses to mark a config `broken` and skip its quality depth, so
a green smoke is the gate for a real run.

---

## 4. Run the full eval

### 4a. Dry-run first (no model launched)

`orchestrate.py` validates the whole harness offline: `configs.json` schema, every `serve_name`
resolves to a case in `~/bin/unsloth-serve`, every `opencode_model_id` is registered in
`~/.config/opencode/opencode.json`, every task dir parses, and the graders/driver compile.

```bash
cd eval/harness
uv run orchestrate.py --dry-run     # must show 0 FAIL before any real launch
```

### 4b. What `configs.json` controls

`eval/harness/configs.json` is the outer loop — one object per `(model, quant)`. Each entry:

```json
{
  "model": "qwen", "quant": "q5",
  "serve_name": "qwen",                              // arg passed to ~/bin/unsloth-serve
  "opencode_model_id": "unsloth/Qwen3.6-35B-A3B-MTP-GGUF",
  "real_ctx": 131072, "probe_max_ctx": 80000,
  "mtp": true, "reasoning": "on", "broken": false
}
```

- Add/remove configs to change the roster. `"broken": true` skips a config entirely (that is how
  `qwen27` is excluded — it smoke-failed both quants).
- `serve_name` must match a `unsloth-serve` case; `opencode_model_id` must be registered in
  `opencode.json`. The dry-run enforces both.
- **To reproduce just one model**, trim `configs.json` to that entry (or use `--only <model>`,
  which filters by the `model` field — note it selects *all* quants of that model).

### 4c. Reps and stages

`orchestrate.py` runs 3 reps per task, split into stages (`REPS_BY_STAGE`):
- **Stage 1** = rep 1 only (screening: smoke + 3× speed probe + 1× the task suite).
- **Stage 2** = reps 2 and 3 (depth → variance/CIs, stable pass-rate).
- Omitting `--stage` runs stage 1 then stage 2 (the full 3×).

Suites and tasks are auto-discovered from `eval/tasks/{A_coding,B_review,C_edit,D_text}/*/meta.json`.
The published set is **10 tasks** (A×4, B×2, C×2, D×2) → 10 tasks × 3 reps = **30 units per
model×quant**.

### 4d. The run commands

Direct (foreground; simplest, one config at a time is fine because it's resumable):

```bash
cd eval/harness

uv run orchestrate.py --resume --stage 1                 # stage 1 across all configs
uv run orchestrate.py --resume --stage 2                 # then depth
uv run orchestrate.py --resume                           # or: both stages in one go
uv run orchestrate.py --resume --only ornith             # restrict to one model (all its quants)
uv run orchestrate.py --resume --stage 2 --only qwen     # one model, one stage
uv run orchestrate.py --resume --agent build             # opencode --agent name (default: build)
```

`--resume` is **mandatory** to launch models (the script refuses without it — `--dry-run` is the
validate-only mode). Resumability is a hard guarantee: a unit is "done" iff
`eval/results/<unit>.json` exists, so re-running the same command just skips completed units and
picks up where it stopped. Kill the process anytime (Ctrl-C / SIGTERM) — you lose at most the
in-flight unit; per-task `timeout_s` (900 s in the tasks) stops a hung model from stalling the run.

Per config, the engine: clears `:8888` → `unsloth-serve <serve_name>` → waits for a real 200 from
`/v1/chat/completions` (zombie/rebind-checked) → 3× speed probe → smoke → each `(suite, task, rep)`
via `opencode_driver.py` + the matching grader(s) → samples RAM once (during the largest-context
unit) → writes the atomic unit JSON → unloads the model before the next config.

### 4e. Detached / unattended runs (recommended for the overnight matrix)

The agent that built this had its tracked background tasks reaped, so the ops layer runs each model
in its **own detached session** with a `caffeinate` wrapper + a janitor watchdog, and reconciles
from on-disk markers:

```bash
cd eval/harness
uv run ops/spawn.py ornith          # detaches run_model.sh ornith → own session; returns immediately
# run_model.sh: caffeinate + watchdog + `orchestrate.py --resume --only <model>` + 6h wall-cap,
# then writes eval/results/DONE__<model>.marker
```

`ops/run_queue.sh` chains every remaining model strictly serially (one in RAM at a time), digesting
each as it finishes and skipping any that fails — the self-driving path for the whole fleet.

### 4f. Where results land

Everything under `eval/results/` (the only tracked eval output; `eval/runs/` is regenerable scratch
and git-ignored):

- `eval/results/<model>__<quant>__<suite>__<task>__rep<N>.json` — one atomic file per completed
  unit (schema in CONTRACT §4: `driver` metrics + `grade` verdict + `ram` sample + `served` info).
- `eval/results/manifest.jsonl` — append-only ledger, one line per unit `{unit_id, status,
  pass_rate, ts}`.
- `eval/results/probe__<model>__<quant>.json` — speed-probe curves.
- `eval/results/smoke__<model>__<quant>.json` — smoke verdict.
- `eval/results/logs/` — serve/orchestrate logs (git-ignored; may contain the endpoint key).

### 4g. Roughly how long

PLAN §7: ~35–40 min per config for stage 1; **~28–32 h at the full 3× across the whole ~17-config
matrix**. It is designed to run overnight, pause, and finish the next day — resume is requirement
#1. A single model×quant at full 3× is roughly 1.5–2 h. The published leaderboard is **450 graded
units across 9 working models**.

---

## 5. Aggregate & score

### 5a. Per-model deterministic digest

After a model's units exist on disk, roll them up with `digest.py` (side-effect-free, this is what
the detached queue runs after each model):

```bash
cd eval/harness
uv run digest.py ornith        # reads results/ornith__*.json + probe__ornith__*.json
# → writes eval/results/DIGEST__ornith.md and prints it
```

Per quant it reports: A_coding pass-rate, C_edit pass-rate + surgical-score + noise-acted count,
B_review recall/precision + hallucination total, D_text unit count (qualitative — judged
separately), speed-probe decode/prefill t/s, tool-call malformed rate, termination breakdown, and
peak RAM. Run it for each model to regenerate all `DIGEST__*.md`.

### 5b. D_text (offline judge)

D_text units are saved by the driver but **not auto-graded** (`grader: "judge"`, `grade: null` in
the unit JSON). They are scored 0–10 by a single offline LLM judge (Opus, to kill judge variance),
and the results are consolidated into `eval/results/DTEXT_JUDGED.json` / `.md`. This is the one
metric that requires a judging pass rather than a deterministic script.

### 5c. Cross-model rollup + composite (the LEADERBOARD numbers)

The metrics `digest.py` doesn't cover (TTFT cold/warm, wall-clock, turns, think:answer ratio, etc.)
are aggregated into `eval/results/METRICS_ROLLUP.md` + `eval/results/metrics_rollup.json`, and the
per-suite `q4/q5` table into `eval/results/LEADERBOARD.md`. The headline composite is one explicit,
auditable weighting (from METHODOLOGY.md / LEADERBOARD.md), applied to each model's **q4** (or
single) quant with decode normalized to the fleet max of 137 t/s:

```
Overall = 0.35·A_coding + 0.25·(1 − tool_malformed%) + 0.15·C_edit
        + 0.10·B_recall + 0.10·(D_text/10) + 0.05·(decode/137)      → ×100
```

To regenerate the LEADERBOARD-equivalent numbers: run `digest.py` for every model (5a), judge the
D_text units (5b), then apply the formula above to the per-model digest values (A pass-rate,
1−tool-malformed%, C pass-rate, B recall, D judge mean, decode t/s). The composite and the
`METRICS_ROLLUP` / `eval/results/LEADERBOARD.md` tables were assembled in the Stage-3 synthesis from
those digest + rollup inputs, not by a single committed scoring binary — the formula is the
reproducible spec, and every input is a deterministic digest field, so the numbers are auditable and
re-derivable from `eval/results/`.

---

## 6. Compare to the published results

The published answer is [`LEADERBOARD.md`](leaderboard.md) (top-level narrative) backed by the
computed [`eval/results/LEADERBOARD.md`](https://github.com/DresvyanskiyDenis/local-llm-coding-bench/blob/main/eval/results/LEADERBOARD.md) and
[`eval/results/METRICS_ROLLUP.md`](https://github.com/DresvyanskiyDenis/local-llm-coding-bench/blob/main/eval/results/METRICS_ROLLUP.md). Compare your regenerated
`DIGEST__*.md` + composite against those tables.

**Non-determinism caveat.** Local LLM inference on Metal is **not bit-reproducible** — sampling,
llama.cpp/Studio version, MTP acceptance, quant build, and background system load all move the
numbers. Expect your figures to land in the **same magnitude and ordering, not identical values**.
That is exactly why the design runs **3 reps per task** (metric #6, stability/variance): a single
pass is noise, and a quant that passes 1/3 is not "keep". Judge a reproduction by whether the
per-dimension winners and the broad composite tiers reproduce, not by matching a score to the
decimal. Known measurement gaps (MTP acceptance rate, the 80 K probe point, long-context decay,
auto-compaction survival) are documented honestly in METHODOLOGY.md and will be null/absent in your
run too unless you extend the task set.
