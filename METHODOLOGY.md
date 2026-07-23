# Benchmark Methodology — Local-LLM Coding Bench

How this benchmark is designed, run, and scored. Grounded in the harness contract
([`eval/harness/CONTRACT.md`](eval/harness/CONTRACT.md)), the master plan
([`eval/PLAN.md`](eval/PLAN.md)), the actual task tree under `eval/tasks/`, the graders under
`eval/harness/graders/`, and the produced results
([`eval/results/METRICS_ROLLUP.md`](eval/results/METRICS_ROLLUP.md),
[`eval/results/LEADERBOARD.md`](eval/results/LEADERBOARD.md)).

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
