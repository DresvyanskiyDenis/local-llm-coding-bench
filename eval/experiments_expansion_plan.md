# Experiments Expansion Plan

*Created 2026-07-25. Companion to [`PLAN.md`](PLAN.md) (the original build contract) and
[`../docs/methodology.md`](../docs/methodology.md) (how the first 450 units were produced).
This document covers **round 2** — what changes and why.*

---

## Why this round exists

Two distinct problems, only one of which was raised externally.

**1. Credibility.** Every task, hidden test, planted-bug key, rubric and judge in the current
suite was authored by Opus. The suite grades itself. This is a fair objection and it is cheaply
fixable by adding externally-authored benchmarks with graders nobody in this project wrote.

**2. Saturation.** Independently of who wrote them, two suites no longer discriminate:

| Suite | Fleet spread | Verdict |
|---|---|---|
| `A_coding` | 0.883 – 0.994 pass-rate | **Saturated.** Seven of nine models above 0.88. Measures "can write Python," not coding ability. |
| `D_text` | 8.67 – 9.83 / 10 | **Saturated.** A 1.2-point spread on a 10-point scale across nine models. |
| `C_edit` | 0.803 – 0.909 | Compressed; seven configs cluster at 0.863. |
| `B_review` | 0.111 – 0.611 recall | **Healthy spread.** The only suite currently separating the fleet. |

Saturation is the more serious scientific problem and no public benchmark fixes it by itself —
the tasks have to get harder.

**The goal is validation, not replacement.** If the round-2 public-benchmark ranking correlates
with the existing composite, the Opus-authored suite is vindicated by external evidence — a
stronger result than discarding it. If it does not correlate, that is a genuine finding. Either
outcome is publishable. See [Validation](#validation--rank-correlation) below.

---

## Decisions at a glance

| Axis | Decision | Grader authorship |
|---|---|---|
| **A_coding** | Replace headline metric with **BigCodeBench Hard** (148 tasks) | External (BigCode project) |
| **New: instruction-following** | Add **IFEval** (541 prompts) | External, **no model in the loop** |
| **B_review** | **Keep**, expand by bug class + add a no-bug control | Ours (defensible — nothing public covers it) |
| **C_edit** | **Keep**, expand noise-comment kinds | Ours (defensible — unmatched in the literature) |
| **D_text** | **Keep**, add long-context + PR-description tasks; switch to pairwise judging | Ours, with method fix |

---

## 1. A_coding → BigCodeBench Hard

**What.** [BigCodeBench](https://github.com/bigcode-project/bigcodebench) Hard split — 148 tasks
requiring correct composition of 3–4 library calls. Two tracks: `Complete` (docstring→code) and
`Instruct` (natural-language→code). **Use the Instruct track** — it is closer to how the models
are actually driven through OpenCode.

**Why this one.** Harder than the current A tasks by construction, so it should restore spread.
Externally authored. Newer than HumanEval (2024), therefore materially less saturated — though
*not* contamination-free, and it must not be described as such.

**Running it.** `--backend openai`, endpoint via `OPENAI_BASE_URL=http://127.0.0.1:8888/v1`.
The official `bigcodebench/bigcodebench-evaluate` Docker image is **amd64-only** (no arm64
manifest). Use `--execution local` to bypass Docker entirely — acceptable here because the code
being executed comes from our own known models, not untrusted third parties.

**Reps: 1, not 3.** Greedy decoding with a deterministic grader; additional reps buy no variance
information. This holds for every externally-graded benchmark in this round.

**Disposition of the existing A tasks.** Keep and keep running them — they become the *easy
floor* of the coding axis, and the A→BigCodeBench-Hard delta per model is itself a result
(which models degrade fastest as difficulty rises). Do not delete them; the 450-unit corpus
stays intact and comparable.

---

## 2. New axis — IFEval

[Google, arXiv 2311.07911](https://arxiv.org/abs/2311.07911) ·
[dataset](https://huggingface.co/datasets/google/IFEval)

**541 prompts, 25 verifiable instruction types.** Every constraint is checked by a short Python
function. Categories:

- **Format** — valid JSON, exactly N paragraphs, markdown sections, bullet lists
- **Length** — at least/at most N words, N sentences, N sentences per paragraph
- **Keywords** — use word X at least N times, never use word Y
- **Content** — start with an exact sentence, end with an exact phrase, include a postscript

**Four reported metrics.** Strict and loose, each at prompt level (every constraint in the prompt
passed) and instruction level (fraction of individual constraints passed).
**Headline = prompt-level strict** — harshest and least gameable.

**Why it belongs here.** It is the cleanest available answer to the authorship objection: there
is no judge, no rubric, no reference answer. A Python function reads the output and returns a
boolean.

**Why it matters for this specific fleet.** `qwen` carries a 28–32% malformed-tool-call tax —
the single most contested finding in the current leaderboard. IFEval measures precisely that
failure mode (can the model hit a mandated output format) on an external axis. Corroboration
there would independently confirm the finding; divergence would be equally informative.

**Follow-on, once IFEval is green: IFBench** — same machinery, 58 constraints IFEval never used.
Published results show models scoring >80% on IFEval but <50% on IFBench, so running both
separates genuine instruction-following from memorisation of these 25 templates.

**Where it lands in the composite.** IFEval is a *new* axis, not a replacement for the existing
`1 − tool_malformed%` term. Report both; decide on re-weighting only after seeing whether they
correlate.

---

## 3. B_review — keep and expand

**Keep, unmodified in kind.** Nothing public plants bugs with a machine-checkable key and scores
recall/precision in a `{file, line, description}` format. The public alternatives surveyed all
fail to match: PrimeVul is binary vulnerable/not-vulnerable classification, Martian Code Review
Bench is LLM-judged against golden comments, and Defects4J/BugsInPy/QuixBugs are flagged as
contaminated in 2025–26 literature. B_review measures something the field does not.

It is also the only suite currently discriminating (0.111–0.611). Expand by **bug class**, not by
task count, so results can report *which kinds* of defects local models miss:

- off-by-one
- concurrency / race
- resource leak
- silently-swallowed exception
- encoding / unicode
- float precision
- timezone / DST
- mutable default argument

**Add a no-bug control file.** Highest-value single addition to this suite. Precision is
currently measured only on files known to contain planted bugs, so a model that hallucinates
freely still scores acceptably as long as it also finds real defects. A control with **zero**
planted bugs yields a clean false-positive rate. Given that every model in the fleet is weak on
this axis, the control is likely to produce the headline finding of the round.

Grader change: `review_grader.py` needs a zero-planted-bug path where recall is undefined
(report `null`, not `0.0`) and precision collapses to `1 − (findings > 0)`.

---

## 4. C_edit — keep and expand

**Keep.** The 2026 audit
[*Edit, But Verify*](https://arxiv.org/html/2604.05100) reviewed 150+ code benchmarks and found
none that plants a deliberately **wrong** instruction and grades non-compliance. CanItEdit and
EDIT-Bench test instructed editing; neither tests instruction *resistance*. This property is
unmatched in the public literature and should be stated as such rather than apologised for.

**Expand by noise *kind*, not count.** Both current tasks use the same species — "a required
pattern must survive." Add:

| Noise kind | What it measures |
|---|---|
| Demands a real but **out-of-scope** refactor | Scope creep |
| Asks for something **already done** | Redundant churn |
| **Contradicts another comment** in the same REVIEW.md | Does it flag the conflict or silently pick one? |

Also vary the ratio — at least one task with **2 noise comments out of 5**, so the model cannot
pattern-match "exactly one is wrong."

`diff_grader.py`'s `noise.json` schema needs a `kind` field; the contradiction case additionally
needs a "did the model surface the conflict" signal, which is the one part of C that cannot be
graded purely by diff.

---

## 5. D_text — expand and fix the judging method

Current D is saturated (8.67–9.83/10) and narrow (summarize + brainstorm). Two additions, both
selected; a third candidate was considered and rejected.

### 5a. Long-context summarization — **highest value**

`methodology.md` already lists as explicitly unmeasured: quality degradation over long context
(#10) and auto-compaction survival (#13), because every current task sits under ~30K tokens,
below OpenCode's ~74K compaction trigger.

Run D1's task shape at **30K / 60K / 100K** context. The speed probe already shows `glm` decode
collapsing ~5× between 2K and 48K while `opus`/`northmini` stay nearly flat — quality almost
certainly moves too, and nothing in the corpus measures it. This converts a documented gap into
a result and is very likely to discriminate.

Grading: key-point recall against a `key_points.json` per context length, so the *same* content
is being recalled at each size and the degradation curve is clean.

### 5b. PR description / commit message from a diff

A task actually performed in practice (there is a `pr-describe` skill in the workflow). Given a
real diff, produce a PR title and body.

Graded on **key-fact recall**, not prose vibes: did it name the changed files, the actual
behaviour change, and any breaking change? This is the same recall-against-key machinery as B,
applied to prose — so it partially escapes the judge problem.

### 5c. Rejected — log / traceback triage

Considered and **not selected**. Overlaps heavily with B_review's diagnostic axis while being
harder to ground-truth than either B or 5b.

### 5d. Method fix — pairwise comparison judging

**Applies to all D tasks, new and existing.** Replace the absolute 0–10 judge with **pairwise
comparison**: show the judge two models' answers to the same task and ask which is better.

Absolute scoring is compressing the entire fleet into 8.7–9.8. Pairwise discriminates far better
at the top of the range and is what Arena-Hard-v2 and WildBench use for exactly this reason.
Same judge, same approximate cost, substantially more resolution.

Implementation notes:
- Randomise presentation order per pair to control position bias.
- Full round-robin at 15 configs = 105 pairs per task. Either accept that cost or use a
  Swiss/bracket scheme; decide when wiring.
- Derive rankings via Bradley–Terry or Elo rather than raw win counts.
- Re-judge the **existing** D answers pairwise so round-1 and round-2 D numbers stay comparable —
  the raw outputs are all saved, so this needs no re-inference.

---

## Validation — rank correlation

The scientific claim of this round. After BigCodeBench Hard and IFEval have run:

Compute **Spearman rank correlation** between the existing composite ranking and each external
benchmark's ranking over the same configs.

- **Correlates** → the Opus-authored suite measures something real, confirmed by graders written
  by third parties. This is the answer to the authorship objection.
- **Diverges** → identifies exactly which axis the home-grown suite was mis-measuring. Also a
  result.

Report the coefficient with its p-value and n, and per-axis as well as on the composite.

**Comparability caveat, to be carried into any writeup.** Published leaderboard numbers for these
model families (Qwen3-30B-A3B ≈ 66 LiveCodeBench, GLM-4.7-Flash ≈ 64, gpt-oss-20b ≈ 60–61) are
all **BF16 vendor checkpoints**. This fleet runs **Q4/Q5/IQ4 GGUF**, and several configs
(`qwen`-MTP, `opus`-distill, `qwopus`, `ornith`) are **community fine-tunes with no public
leaderboard entry at all**. Any gap should be attributed first to quantisation plus serving-stack
delta. Use public numbers for "are we in the right ballpark," never as apples-to-apples.

---

## Pre-flight checks

Cheap, and each one can invalidate an estimate below. Do before building.

| # | Check | Cost |
|---|---|---|
| 1 | `bigcodebench.evaluate --subset hard --execution local` produces a score on one config | 30 min |
| 2 | IFEval via `lm-evaluation-harness` `local-chat-completions` against `127.0.0.1:8888/v1` | 30 min |
| 3 | Confirm BigCodeBench Hard runtime per config → extrapolate to 15 | included in #1 |

---

## Effort and run scale

| Item | Build | Run (15 configs) |
|---|---|---|
| BigCodeBench Hard | 3–5 h | 1 rep — overnight |
| IFEval | ~1 h | 1 rep — overnight |
| B_review expansion (8 classes + control) | 1–2 d | 3 reps, per existing methodology |
| C_edit expansion (3 noise kinds) | ~1 d | 3 reps |
| D long-context (3 sizes) | ~1 d | 3 reps |
| D PR-description | ~0.5 d | 3 reps |
| Pairwise re-judge (incl. round-1 answers) | ~0.5 d | no re-inference needed |

**Harness.** `inspect-ai` (`uv add inspect-ai`) is the recommended single surface — it ships
IFEval, and its `Task`/`Solver`/`Scorer` abstraction is where the existing B/C/D tasks can be
re-hosted alongside the public benchmarks. `lm-evaluation-harness` is the faster path to a
first IFEval number if inspect-ai wiring stalls.

> **SUPERSEDED — neither harness was adopted.** IFEval shipped instead as a standalone adapter,
> [`external/ifeval/`](external/ifeval/README.md), which vendors google-research's
> `instruction_following_eval` unmodified and posts straight to `127.0.0.1:8888/v1`; its
> *"Why not `lm-evaluation-harness`"* section records the reason (`lm-eval` declares `torch` as a
> core dependency, which this eval stack deliberately avoids). **`inspect-ai` was simply not
> adopted — it was never evaluated on record**, and no other file in this repo mentions it, so do
> not read this paragraph as a rejection with reasoning behind it. The same applies to pre-flight
> check #2 above. What was actually built is in
> [`IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md).

---

## Deferred and not selected

**Deferred — Terminal-Bench 2.1 via Harbor (whole-harness evaluation).** The only public runner
in 2026 with a genuine bring-your-own-agent contract: subclass `BaseAgent`
(`name()`, `version()`, `setup(environment)`, `run(instruction, environment, context)`),
register via `harbor run -d terminal-bench/terminal-bench-2-1 --agent-import-path path.to:Agent`.
Harbor runs on LiteLLM, so `api_base` reaches `127.0.0.1:8888/v1`;
[badlogic/pi-terminal-bench](https://github.com/badlogic/pi-terminal-bench) is a working template
for wrapping a third-party CLI agent; and the 2.1 leaderboard already carries an open-weight
entry, so open models are accepted in practice.

Deferred because it is roughly a week (adapter, unresolved arm64 story, container→host
networking, 89 Dockerized tasks per config on a laptop) and it answers a different question than
the one this round addresses. Revisit after rounds 1–2 land; pitch on its own merits.

**Not selected:**

- **Any SWE-bench variant.** OpenAI
  [deprecated Verified in Feb 2026](https://openai.com/index/why-we-no-longer-evaluate-swe-bench-verified/)
  (contaminated; ~59% of failures had broken tests) and
  [retracted the SWE-bench Pro recommendation in July 2026](https://alphasignal.ai/news/openai-retracts-swe-bench-pro-after-finding-30-of-tasks-broken)
  (~30% broken tasks). Citing either would mean citing what the field just discredited.
- **HAL (Princeton).** Best-designed scaffold-agnostic contract surveyed; submissions paused and
  leaderboard no longer updating.
- **MCP-specific benchmarks** (MCPBench, MCP-Bench, MCPEval, LiveMCPBench, MCP-RADAR,
  MCP-AgentBench). None confirmed to accept a custom client, and they test MCP tool use in the
  abstract rather than this harness. *(Note: MCP-Universe **does** support local endpoints
  natively — `mcpuniverse/llm/openai.py` exposes `base_url`, plus a dedicated `local_llm.py`;
  its README's "OpenAI/Anthropic/Google only" framing is wrong. Recorded for future reference.)*
- **EvalPlus (HumanEval+/MBPP+).** Zero adaptation cost and a native `--base-url` flag, but
  heavily contaminated and near-saturated — it would reproduce exactly the problem
  BigCodeBench Hard is being adopted to solve. Available as a cheap sanity floor if ever wanted.
- **LiveCodeBench.** The only contamination-resistant-by-construction option (date-windowed via
  `--start_date`/`--end_date`), and the strongest citation available. Not selected this round
  only because it needs a patch to `lcb_runner/lm_styles.py` to accept a `base_url`. **The
  first candidate for round 3.**
- **CanItEdit / EDIT-Bench.** The only human-authored instructed-editing benchmarks with
  test-based grading. Superseded here by keeping and expanding C_edit, which tests strictly more.
- **Log / traceback triage** as a D task — see §5c.
