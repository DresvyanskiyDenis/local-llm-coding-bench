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

---

## 6. Round 2 — two lanes, external graders, expanded suites

*Added 2026-07-25/26, branch `feature/round2-expansion`. Companion docs:
[`eval/experiments_expansion_plan.md`](../eval/experiments_expansion_plan.md) (what and why),
[`eval/IMPLEMENTATION_PLAN.md`](../eval/IMPLEMENTATION_PLAN.md) (how, in this repo), and the live
build/run record [`eval/ROUND2_STATUS.md`](../eval/ROUND2_STATUS.md).*

### 6.1 Why: credibility and saturation

Every task, hidden test, planted-bug key, rubric and judge in round 1 was authored by Opus — the
suite grades itself, a fair objection. Independently of who wrote them, two suites had also
stopped discriminating: `A_coding` (0.883–0.994 pass-rate, seven of nine models above 0.88) and
`D_text` (8.67–9.83/10, a 1.2-point spread on a ten-point scale). `B_review` (0.111–0.611 recall)
remained the one suite still separating the fleet. Round 2 answers both problems at once: external,
third-party-authored graders for credibility, and harder or expanded tasks for spread. The goal is
validation, not replacement — see §6.7.

### 6.2 Two lanes — do not conflate them

This is the central methodological change this round makes, and the docs exist to prevent it being
flattened back into one number.

- **Lane 1 — in-harness** (suites A/B/C/D, including the round-2 expansions in §6.8). Runs through
  OpenCode exactly like round 1: multi-turn, tool-using, agentic. It measures **the model plus the
  harness** — tool-call formatting, context handling, and compaction behaviour all count toward
  the score.
- **Lane 2 — external** (BigCodeBench Hard, IFEval). Single-turn, direct
  `POST /v1/chat/completions`, no OpenCode, no agent, no tools in the loop. It measures **the
  model** in isolation.

A model can rank well in one lane and poorly in the other. That is not an inconsistency to be
explained away — it is informative on its own terms. If, say, `qwen`'s malformed-tool-call tax
(28–32%, the most contested finding in round 1) shows up as an in-harness weakness with no
equivalent degradation on IFEval, that points at the harness/tool-formatting integration rather
than raw instruction-following. If IFEval shows the same weakness, that is evidence the problem is
in the model. Report both lanes per model; never average across them into a single number.

### 6.3 Lane 2, axis 1 — BigCodeBench Hard (replaces A's headline metric)

[BigCodeBench](https://github.com/bigcode-project/bigcodebench) Hard, Instruct track — 148 tasks
requiring correct composition of 3–4 library calls, run greedy at 1 rep (deterministic grader,
additional reps buy no variance information). Newer and materially less saturated than the
existing A tasks, though not contamination-free.

**Execution and comparability — this caveat belongs next to every `pass@1` number, not only here.**
BigCodeBench's official evaluator is a Docker image with no arm64 manifest, and its pinned
`requirements-eval.txt` (`numpy==1.21.2`, `numba==0.55.0`, `keras==2.11.0`, …) has no
Apple-Silicon wheels. The remaining official path, the Gradio remote executor, uploads generated
solutions to a third-party HF Space — rejected on that basis alone. This repo instead installs the
same ~71 packages **unpinned** and runs `--execution local`. Confirmed on this machine:
**148/148 Hard tasks resolvable, 0 blocked** — but **37 packages sit at a different version than
upstream's pinned set** (e.g. numpy 1.21.2 → 2.4.6, pandas 2.0.3 → 3.0.5, Django 4.2.7 → 6.0.7;
full mapping in `eval/external/bigcodebench/PROVENANCE.md`).

Consequence: every config runs under the *identical* relaxed-pin executor, so the **within-fleet
ranking is valid** — that is what the Spearman correlation in §6.7 needs. The **absolute `pass@1`
is not comparable to the public BigCodeBench leaderboard** and must never be quoted as if it were.
Each result JSON carries this in a `comparability` field for exactly this reason.

The existing A tasks stay in the tree, unreplaced — they become the easy floor of the coding axis,
and the A → BigCodeBench-Hard delta per model is itself a result (which models degrade fastest as
difficulty rises).

### 6.4 Lane 2, axis 2 — IFEval (new axis)

[Zhou, Lou et al., arXiv:2311.07911](https://arxiv.org/abs/2311.07911) (Google Research) — 541
prompts, 25 programmatically-verifiable instruction types (format, length, keywords, content).
Every constraint is checked by a short deterministic Python function: no LLM judge, no reference
answer, no rubric. Four metrics, each strict (raw response) and loose (8 lightly-normalized
variants — with/without first line, last line, both, `*` stripped):

| Metric | Meaning |
|---|---|
| `prompt_level_strict` | fraction of prompts where every tagged instruction passed, strict — **headline** |
| `inst_level_strict` | fraction of individual instruction checks passed, strict |
| `prompt_level_loose` / `inst_level_loose` | same, loose variant |

`by_instruction_type` breaks `inst_level_strict` down per instruction id — not decoration, it is
what turns "qwen is bad at formats" into "qwen fails *these* format classes," the fine-grained
corroboration (or refutation) of the round-1 malformed-tool-call finding.

### 6.5 Reasoning-leak handling — affects how every round-2 number is read

The served (thinking) models in this fleet emit a literal `<think>…</think>` block **inside**
`choices[0].message.content`. Confirmed live against a served config (`qwen`) as a property of the
serving stack itself rather than a per-model output convention — though not yet re-probed against
every model individually. `message`'s keys are exactly `content`, `refusal`, `role`: there is no
`reasoning_content` field, and `usage.completion_tokens_details.reasoning_tokens` reports `0`. The
leak is therefore **invisible at the API level** — nothing in the response envelope flags that
reasoning happened, so it can only be detected and removed textually, by pattern-matching the tag
in the content string itself.

Both external adapters strip `<think>`/`<reasoning>`/`<thinking>` blocks from the response before
scoring, **on by default**. The conservative case is truncation: a thinking model can spend its
entire token budget on reasoning and return `finish_reason: "length"` with an *opening* `<think>`
and no closing tag. That response is not "mostly reasoning, a bit of answer" — it is reasoning,
full stop — so the stripper discards it entirely, yielding an **empty** response rather than
leaking a partial chain-of-thought into the scored text. An empty response then legitimately fails
the grader (every IFEval instruction, or no BigCodeBench program at all) — correct scoring, not a
bug — but it must stay *visible* as such: result JSONs separately count
`n_finish_length`/`n_empty_after_strip` (IFEval) and `n_empty_completions`/`n_sanitizer_dropped`
(BigCodeBench), so a near-zero score on a thinking config reads as "it never reached an answer
within the token budget," not "it ignored every instruction." Scoring a truncated `<think>` as if
it were the answer would silently corrupt every downstream number; discarding it and counting the
discard is the conservative choice.

### 6.6 Composite — unchanged; new axes reported alongside

**The composite formula in §4 is not modified by round 2.** BigCodeBench Hard and IFEval are new,
**unweighted** axes reported next to the existing composite, not folded into it:

```
Overall = 0.35·A_coding + 0.25·(1 − tool_malformed%) + 0.15·C_edit
        + 0.10·B_recall + 0.10·(D_text/10) + 0.05·(decode/137)      → ×100   [unchanged]

+ bcb_hard_pass@1        (reported, unweighted, within-fleet only — §6.3)
+ ifeval_prompt_strict   (reported, unweighted — §6.4)
```

Re-weighting the composite to include either axis is deliberately deferred until the rank
correlation (§6.7) between the composite and the external rankings is known — folding an axis in
before checking whether it agrees with or diverges from the existing ranking would beg the
question the round exists to answer.

### 6.7 Validation — rank correlation (the scientific claim of this round)

Once BigCodeBench Hard and IFEval have full-fleet results, Spearman rank correlation is computed
between the existing round-1 composite ranking and each external benchmark's ranking over the same
configs, reported with its p-value and n, per axis and on the composite. A significant positive
correlation is the answer to the authorship objection — the Opus-authored suite measures something
real, confirmed by graders written by third parties. A divergence identifies exactly which axis the
home-grown suite was mis-measuring; either outcome is reported, not just the one that flatters the
round-1 suite.

**Comparability caveat for this correlation, too.** Published leaderboard numbers for these model
families are BF16 vendor checkpoints; this fleet runs Q4/Q5/IQ4 GGUF, and several configs (`qwen`
MTP, `opus` distill, `qwopus`, `ornith`) are community fine-tunes with no public leaderboard entry
at all. Any gap between this fleet's numbers and published ones should be attributed first to
quantization plus serving-stack delta — public numbers are useful for "are we in the right
ballpark," never as an apples-to-apples comparison.

### 6.8 B_review, C_edit, D_text — kept, expanded by kind, D re-judged pairwise

`B_review` and `C_edit` measure something not matched in the current public literature (planted
bugs with a machine-checkable key, scored for recall *and* precision; a deliberately wrong
instruction graded for non-compliance rather than compliance) and are kept, expanded by *kind*
rather than by count, so results can report which specific failure modes local models miss:

- **B_review** gains four task directories covering eight bug classes (off-by-one,
  concurrency/race, resource leak, swallowed exception, encoding/unicode, float precision,
  timezone/DST, mutable default argument) plus a **no-bug control** (`B6_control_nobugs`) — a file
  with zero planted bugs, so precision is measured with a clean false-positive rate instead of only
  on files already known to contain bugs. `review_grader.py`'s control path reports recall as
  `null` (undefined, not `0.0`) and precision as `1 − (findings > 0)`.
- **C_edit** gains three noise kinds beyond "a required pattern must survive": scope creep (an
  out-of-scope refactor is demanded), redundant churn (asks for something already done), and a
  contradiction between two review comments in the same file (does the model surface the conflict
  or silently pick one) — plus a task with 2 noise comments out of 5, so the model cannot
  pattern-match "exactly one comment is wrong."
- **D_text** gains long-context summarization at 30K/60K/100K tokens sharing one identical core
  document (so the degradation curve measures degradation, not a content change) and a
  PR-description-from-diff task graded by key-fact recall. **All D tasks, new and existing, switch
  from absolute 0–10 judging to pairwise comparison** (Bradley–Terry over judged pairs, position
  bias measured via randomized presentation order per pair) — absolute scoring was compressing the
  entire fleet into an 8.7–9.8 band; pairwise discriminates better at the top of the range, the
  same reason Arena-Hard-v2 and WildBench use it. Round-1 D answers are re-judged pairwise so
  round-1 and round-2 D numbers stay on a comparable method (see `eval/ROUND2_STATUS.md` for how
  the round-1 answer text was recovered from OpenCode's session storage after the original
  `eval/runs/` scratch directory had been cleaned).

### 6.9 Vendored graders

Both external verifiers — IFEval's `instruction_following_eval` package and BigCodeBench's
`evaluate`/`generate` modules — are vendored or installed **unmodified**, with a `PROVENANCE.md`
per component recording source URL, version, sha256, and fetch date
(`eval/external/ifeval/vendor/PROVENANCE.md`, `eval/external/bigcodebench/PROVENANCE.md`). Every
deviation from upstream defaults is expressed as a CLI flag (e.g. `--execution local`,
`--max-new-tokens 4096`, relaxed rlimits on macOS), never a source edit, and is logged in the
result JSON. The point: the grader that decides whether a response passes IFEval or BigCodeBench
Hard is code nobody on this project wrote. That is what makes it usable as an independent check on
the Opus-authored suite rather than another instance of the same authorship problem.

### 6.10 Reproducing the external lane

Detailed setup — venv bootstrap, environment-health checks, exact flags, and the known upstream
quirks worked around — lives in each benchmark's own README, not duplicated here:
[`eval/external/ifeval/README.md`](../eval/external/ifeval/README.md),
[`eval/external/bigcodebench/README.md`](../eval/external/bigcodebench/README.md). Minimal
copy-pasteable entry points:

```bash
# put :8888 in eval mode (stops llama-swap, hands the port to unsloth-serve)
eval/harness/ops/serving_mode.sh eval

# IFEval — one config, 20 prompts, live acceptance check
uv run eval/external/ifeval/run_ifeval.py --only opus --limit 20

# BigCodeBench Hard — one config, 10 tasks
uv run eval/external/bigcodebench/run_bcb.py --only opus --limit 10

# hand the port back for daily OpenCode use
eval/harness/ops/serving_mode.sh daily
```

Live build and run status — what has actually executed on this machine, and what is still pending
a sizing decision (the full 541-prompt IFEval suite runs ~44 h across 15 configs and needs a
subsampling call before an overnight run fits) — is tracked in
[`eval/ROUND2_STATUS.md`](../eval/ROUND2_STATUS.md), not here: this document describes method,
that one describes progress.
