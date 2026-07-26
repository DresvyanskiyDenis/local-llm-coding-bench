# Round 2 — build status

*Session of 2026-07-25/26, branch `feature/round2-expansion`. Live document: it is written as the
phases land, so a usage-limit stop leaves an honest record rather than a silence.*

Gate definitions are [`IMPLEMENTATION_PLAN.md` §9](IMPLEMENTATION_PLAN.md#9-execution-order-for-the-night).

## Phase status

| # | Phase | Gate | Status |
|---|---|---|---|
| 0 | vendor + venvs + env_health + reasoning leak | sha256s recorded, `env_health.json` written, leak answer recorded | ✅ green |
| 1 | IFEval adapter | `--limit 20` scores one config, four metrics populated | 🟠 runs, but two numbers need Denis — see below |
| 2 | BigCodeBench adapter | `--limit 10` gives `pass@1` with `n_env_errors == 0`, wall-clock recorded | 🟡 in flight |
| 3 | grader changes | round-1 fixtures re-grade byte-identically; control returns `recall: null` | ✅ green |
| 5 | pairwise judge | runs end-to-end on round-1 D answers; order effect estimated | 🟠 unblocked by a recovery — see below |
| 6 | `aggregate.py` | reproduces the **existing** `docs/leaderboard.md` composite from result files | ✅ green |
| 4 | 11 new task dirs | each B bug proven by `verify_bugs.py`; C ref solutions pass; D token counts measured | 🟡 in flight |

### Phase 0 — green, with evidence

The `clear_port()` guard was verified **live**, not by reading it. With llama-swap holding `:8888`,
the guard refused and exited:

> `REFUSING to clear :8888: it is held by llama-swap (pid 67539 …), not by an eval server. Killing
> it would take OpenCode's daily fleet down. Put the machine in eval mode first…`

llama-swap survived the attempt. This is the failure that would otherwise have taken the daily
coding fleet down silently in the middle of an overnight run.

`orchestrate.py` remains additive-only: `--dry-run` reports **10 PASS / 0 PENDING / 0 FAIL**, and
`planned_units()` still yields 30 units for stages `[1,2]`, 10 for stage `[1]`, reps `[1,2,3]`.

### Phase 3 — green, with evidence

18/18 grader fixtures pass, and — the part that actually mattered — **8/8 backward-compatibility
fixtures re-grade byte-identically** against round 1. The new no-bug control returns `recall: null`,
and `digest.py:23-25` filters non-numerics out of the mean, so a `null` drops out of the B average
instead of dragging it to zero. That was verified by reading the code, not assumed.

### Phase 6 — green, with evidence

`aggregate.py` reproduces the hand-written `docs/leaderboard.md` composite from the result files
alone: **9/9 models agree to one decimal place**, max |Δ| = 0.050, rank order identical.

| model | leaderboard | recomputed |
|---|---|---|
| ornith | 88.3 | 88.35 |
| gemma | 87.1 | 87.08 |
| qwopus | 87.0 | 87.03 |
| opus | 86.6 | 86.60 |
| glm | 84.9 | 84.89 |
| northmini | 83.7 | 83.66 |
| qwen | 83.0 | 83.01 |
| katdev | 82.2 | 82.19 |
| gpt-oss | 77.1 | 77.14 |

## Environment health

BigCodeBench relaxed-pin local execution, resolved against the vendored venv
(`eval/external/bigcodebench/env_health.json`), Python 3.12.13 / Darwin-25.5.0-arm64:

- hard tasks: **148** · resolvable: **148** · blocked: **0**
- distinct third-party modules imported by the task set: **87** · missing: **none**
- version shifts vs the upstream pinned set: **37**

Zero blocked tasks is the number that matters — the local executor can actually run the whole hard
split. The 37 version shifts are the price of relaxed pins and the reason for the caveat below.

> **Caveat, to be repeated wherever the number appears:** BigCodeBench pass@1 here is a
> **within-fleet** number. Execution is local with relaxed pins — not the upstream Docker image —
> so it ranks *our* configs against each other and is **not comparable to the public leaderboard**.

## Reasoning leak

**Confirmed, and in the worst of the possible shapes.** Probed live against a served config:

- `choices[0].message` keys are exactly `['content', 'refusal', 'role']` — there is **no
  `reasoning_content` and no `reasoning` field**
- `completion_tokens_details.reasoning_tokens: 0`
- `content` begins with a literal `<think>`
- at a 512-token cap, `finish_reason: "length"` with **no closing `</think>`** — the entire budget
  went to reasoning

So the leak is invisible to the API and can only be handled textually. Consequences, applied to all
three affected lanes:

1. Stripping is **mandatory**, not opt-in; `--strip-reasoning` defaults ON.
2. A response truncated mid-`<think>` must strip to **EMPTY**. It must never leak thinking into the
   graded answer — a partial chain-of-thought scored as if it were the reply would corrupt every
   number downstream.
3. Emptiness must be **counted and distinguishable**: `n_finish_length`, `n_empty_after_strip` and
   `n_empty_completions` are all separate from `n_env_errors`.

The probe also confirmed `eval_proxy.py` does its job: the client sent `null` for all six sampling
parameters and the proxy forced the neutral block onto the upstream request.

*Record-keeping note:* the probe ran against `qwen4`, not `opus4` as originally briefed. The finding
is a property of the serving stack rather than of one model, but it has not been re-probed per model.

## Measured wall-clock

### IFEval — measured, and it does not fit

| quantity | value |
|---|---|
| gate run | opus q4, `--limit 20`, `max_tokens 1280` |
| wall-clock | 388 s → **19.4 s/prompt** |
| full suite | 541 prompts → ~2.9 h per config |
| **15 configs** | **~44 h** |

44 h is not an overnight run, and the fix for the truncation problem below (a higher token cap)
makes it worse. A seeded stratified subsample is the obvious lever, but its size is Denis's call —
see *Needs Denis*.

### BigCodeBench

_pending — Phase 2 gate in flight._

## What actually has to be re-run — 11 tasks, not 21

Round 1's results are **complete and reusable**: all 10 original tasks have 45 unit results each
(15 configs × 3 reps). Phase 3 proved the graders re-grade round-1 fixtures **byte-identically**,
which is precisely what licenses reusing them — had that gate come back red, everything would need
re-running.

So the round-2 in-harness run is **the 11 new tasks × 15 configs**, not all 21. The mechanism is
already there: the per-task reps/configs override in `planned_units()` — the one permitted change to
`orchestrate.py`.

The new tasks sit **inside** the existing suites rather than beside them, so the suite scores
genuinely strengthen:

| suite | round 1 | round 2 | composite weight |
|---|---|---|---|
| A_coding | 4 | **4 — unchanged** | 0.35 |
| B_review | 2 | **6** | 0.10 |
| C_edit | 2 | **5** | 0.15 |
| D_text | 2 | **6** | 0.10 |

**A is the exception, and it explains why the external lane exists.** A is saturated at 0.883–0.994
— every config is at the ceiling, so it no longer separates anything, and adding four harder
hand-written tasks would just be guessing where the ceiling is. **BigCodeBench Hard is the
strengthened A**: 148 genuinely hard tasks in place of 4 saturated ones. It is not a parallel
curiosity; it replaces an axis that stopped working. IFEval is a straightforwardly new axis —
instruction-following was never measured here at all.

D is treated twice over: harder tasks (the 30K/60K/100K ladder) *and* a better scoring method
(pairwise Bradley-Terry instead of absolute scores that saturated at 8.67–9.83).

## Composite change — decided 2026-07-26

Two decisions by Denis that change the composite. It is **no longer the round-1 quantity** and every
place it appears must say so.

**1. `tool_malformed%` drops from 0.25 to 0.10.** The round-1 data is bimodal, not saturated:

| | configs | value |
|---|---|---|
| working | gemma, glm, katdev, opus, qwopus | 2.4 – 5.5 % |
| worse | ornith, gpt-oss | 8.7 – 10.5 % |
| broken | northmini, qwen | 17.9 – 32.5 % |

The outliers are 5–10× worse, so even a small weight punishes them decisively. Meanwhile the
differences *inside* the 2–5 % cluster are 3 versus 5 malformed calls out of ~100 — noise, and noise
should not carry a quarter of the composite.

**2. A stops being four saturated hand-written tasks.** BigCodeBench Hard tasks are wrapped as
ordinary in-harness A tasks (`repo/` + `PROMPT.md` + the existing `pytest_grader.py`), so A
discriminates again *without* ceasing to be a harness-level measurement. A keeps its 0.35.

The wrapped tasks are deliberately **the same tasks the external lane runs directly**. Same task, two
delivery modes — through OpenCode with tools and turns, versus single-turn straight at the endpoint.
The difference between them **isolates the harness contribution**. That is a controlled comparison
rather than two metrics reported side by side, and it is the answer to "why measure the model at all
when the harness is the product": the model-level number is the control that makes the harness-level
number interpretable.

Proposed redistribution of the freed 0.15 — weight follows spread, so B (0.111–0.611, the healthiest
axis in round 1) gains most and the narrow C (0.803–0.909) gains least:

```
0.35·A + 0.10·(1 − tool_malformed%) + 0.20·C + 0.20·B_recall + 0.10·(D/10) + 0.05·(decode/137)
```

*Awaiting Denis's confirmation of the split; the two weight decisions themselves are settled.*

## Needs Denis

1. **IFEval run size.** At full 541 prompts the suite costs ~44 h across 15 configs. A seeded
   stratified subsample recorded as `n_prompts` vs `n_prompts_available` would fit the night, but
   choosing the size is a judgement about how much per-instruction-type resolution to trade away —
   541 prompts span 25 instruction types, and a subsample small enough to fit 8 h leaves some types
   at single-digit n, which turns `by_instruction_type` into noise. A sizing table is being measured
   rather than guessed.

2. **IFEval token cap.** The gate run truncated **15 of 20** responses at `max_tokens 1280`. Given
   the confirmed reasoning leak, `prompt_level_strict: 0.25` may be measuring "did it finish
   thinking in time" rather than instruction-following. A 4096-token re-run on the truncated slice
   is being measured to size the effect. Raising the cap and shrinking the sample pull against each
   other — that trade is item 1.

3. **Pairwise judge budget — measured in the unit that actually binds.** The judge runs on a Pro
   subscription, so the `total_cost_usd` that `claude -p` reports ($0.070/call) is a notional API
   price, not money anyone pays. The scarce resource is the **usage limit**, and the honest measure
   is tokens:

   | per judge call | tokens |
   |---|---|
   | cache creation | 11,465 |
   | cache read | 3,289 |
   | output | ~11 |

   The full 210-pair round-robin is therefore ≈ **2.4 M cache-creation tokens**. That is the number
   to weigh against a 5 h/7 d limit — and it is not hypothetical: this session hit its limit twice
   in one night, which is what killed the first judge run and every other agent with it.

   **The `cache_creation` ≫ `cache_read` ratio is itself a defect.** Each pair is a fresh `claude -p`
   process, so the system prompt is re-cached from scratch every single call instead of being read
   back. A judge that holds one process open, or otherwise shares a cacheable prefix across pairs,
   would collapse most of that 2.4 M. Worth fixing before authorising the full round-robin —
   otherwise the remaining ~180 pairs cost far more limit than the work justifies.

   Unattended spend stays capped at a reduced but *real* pass (~30 pairs across both tasks) so the
   order-effect and Bradley-Terry paths run on genuine judgements; the remaining pairs await your
   authorisation. The cache makes the remainder resumable. Any partial Bradley-Terry fit is labelled
   partial wherever it appears.

4. **`tool_malformed%` carries weight 0.25 and is measured across all runs, so adding 11 tasks
   changes it.** Two defensible options, and it is your call because it is a comparability
   judgement, not a technical one:
   - *Keep the round-1 value* and report the new tasks' malformed rate separately — the composite
     stays strictly comparable to round 1, at the cost of ignoring better evidence.
   - *Recompute over old + new* — a more reliable estimate over roughly three times the data, but
     the composite is then no longer the same quantity as round 1's and must be labelled as such.

   I lean to recomputing and labelling it, since 0.25 is a large weight to leave resting on the
   smaller sample. Either way it must be stated explicitly wherever the composite appears.

5. **Round-1 answers are now tracked — keep it that way.** See the blocker below. The recovered
   answers live in `eval/results/round1_answers/`, which is **in git on purpose**. If a future
   cleanup gitignores it again, the next round of pairwise judging becomes impossible without
   re-running inference.

## Incident — the machine was left with no server for four hours

At 20:34 the machine was put into `eval` mode. The IFEval gate finished at 20:41. At 20:53 the
session hit its usage limit and every agent died at once — including the one holding the port.

Nothing restored `daily` mode. From 20:41 until roughly 00:50 the machine sat with **`.serving_mode`
= eval, nothing listening on `:8888` or `:8899`, no llama-swap process, and the launchd job
unloaded**. Denis's daily OpenCode fleet was down that whole time, for no benefit — no gate was
running either.

Restored with `serving_mode.sh daily`: llama-swap pid 20309 is on `:8888`, launchd job loaded,
state file back to `daily`.

**The gap this exposes.** The Phase 0 `clear_port()` guard protects llama-swap from being *killed by
accident*. It does nothing about llama-swap being *stopped deliberately and never restarted* — which
is what happened. The guard is not a substitute for someone owning the restore, and an agent that
dies mid-run owns nothing. Worth a watchdog before the real 15-config night: eval mode should not be
a state the machine can be left parked in.

## Open finding — the pairwise judge's order effect is implausibly extreme

The re-run works mechanically: **76 real judgements** of the 210-pair design, `n_backend_errors: 0`,
`n_unparseable: 0`, fully cache-resumable, and the partial run is labelled unmissably. Separating
backend failures from genuine unparseables — the defect that silently wasted 30 calls on the first
attempt — is fixed and demonstrated.

But the order effect reads:

| task | first-position win rate | decisive games |
|---|---|---|
| D1_summarize_mtp | **0.109** | 46 |
| D2_dedup_approaches | **0.100** | 30 |

The answer shown *second* wins roughly nine times in ten. Unbiased is 0.5, and genuine positional
bias in LLM judges typically lands at 0.55–0.70. **0.10 across 76 decisive games is not noise and is
far outside the usual range**, which makes a label-mapping bug at least as likely as real recency
preference — presentation order randomised per pair while the returned A/B verdict is interpreted
against the pre-shuffle order would invert results exactly like this.

**No Bradley-Terry strength from this run is readable until that is resolved**, and judging more
pairs first would only buy a more confident wrong answer. Diagnosis in progress: same pair re-judged
in both orders, an identity control (both sides the same text — a sane judge returns TIE), and a
read of the fully rendered prompt to confirm the A/B labels match the answers actually sent.

If it proves to be genuine bias, the fix is a swap-and-rejudge pass (each pair in both orders,
combined), which doubles the pair count and must be priced in usage-limit tokens before it runs.

## Blockers

### Resolved — round-1 D_text answers were unrecoverable, then recovered

Phase 5 was designed on the expansion plan's premise that round-1 answers are all saved, so
re-judging needs no re-inference. **On this machine that premise was false.** `eval/runs/` — the only
place `<rundir>/answer.txt` was ever written — is gitignored, regenerable-by-design, and had been
cleaned: 0 entries. The tracked unit JSONs keep only token *counts* (`driver.tokens.answer`), and
`DTEXT_JUDGED.json` keeps only the offline judge's own comments, not the models' text. The agent
building Phase 5 correctly refused to fabricate verdicts and reported 0 of 30 answers found; that
refusal was the right call and is why this was caught rather than quietly faked.

The answers were recoverable because every unit JSON records `driver.session_id`, and OpenCode keeps
its sessions in its own data directory — which was never gitignored or cleaned.
`eval/harness/ops/recover_round1_answers.py` walks the D_text rep-1 units, runs `opencode export`
per session and writes each final assistant answer to `eval/results/round1_answers/D_text/`.
**30/30 recovered**, all non-trivial, now tracked in git so this cannot happen a third time.

No round-1 result file was modified in the process; `eval/results/*.json` from round 1 stays
immutable.
