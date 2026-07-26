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

3. **Pairwise judge budget — now measured, not estimated.** One `claude -p` judge call costs
   **$0.070** (11,465 cache-creation tokens per invocation; the system prompt is re-cached every
   time). The full D1+D2 round-robin is 210 pairs ≈ **$14.70**. Unattended spend is capped at a
   reduced but *real* pass (~30 pairs across both tasks, ≈ $2.10) so the order-effect and
   Bradley-Terry paths run on genuine judgements; the remaining ~180 pairs await your authorisation.
   The result cache makes the remainder resumable without re-spending. Any partial Bradley-Terry fit
   is labelled partial wherever it appears.

4. **Round-1 answers are now tracked — keep it that way.** See the blocker below. The recovered
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
