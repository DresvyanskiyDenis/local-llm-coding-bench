# AGGREGATE — round 1

*Generated 2026-07-28T07:56:40.199682+00:00 by `eval/harness/aggregate.py`. 450 units over 10 tasks found on disk (task set defines 10).*

```
Overall (round1 weights, published) = 0.35*A_coding + 0.25*(1 - tool_malformed%) + 0.15*C_edit + 0.10*B_recall + 0.10*(D_text/10) + 0.05*(decode/137) -> x100
Overall (round2 weights)            = 0.35*A_coding + 0.10*(1 - tool_malformed%) + 0.20*C_edit + 0.20*B_recall + 0.10*(D_text/10) + 0.05*(decode/137) -> x100
```

> **Non-comparability:** The round-2-weighted composite is NOT the same quantity as the round-1 leaderboard composite and must never be compared to docs/leaderboard.md or eval/results/LEADERBOARD.md as if it were. Two independent things changed: (1) the weights themselves (tool_malformed 0.25->0.10, B_recall +0.10, C_edit +0.05 -- see ROUND2_REWEIGHT_REASON), and (2) for any aggregation that includes round-2 tasks (--round 2 / --round all), A_coding itself changed shape -- round-1 A was 4 saturated hand-written tasks (0.883-0.994 pass-rate); round-2 A5-A14 wrap BigCodeBench-Hard, so A is now 14 tasks of a materially different difficulty. This caveat belongs next to every round-2-weighted number, not in a footnote.

## Gate — does this reproduce the hand-written leaderboard?

**REPRODUCED: 9/9 models agree to 1 decimal place (max |delta| 0.050)**  ·  rank order identical: **True**

| Model | Quant | Published | Computed | Computed (1dp) | Δ | Agrees @1dp |
|---|---|--:|--:|--:|--:|:--:|
| `ornith` | q4 | 88.3 | 88.35 | 88.3 | +0.050 | OK |
| `gemma` | q4 | 87.1 | 87.08 | 87.1 | -0.020 | OK |
| `qwopus` | q5 | 87.0 | 87.03 | 87.0 | +0.030 | OK |
| `opus` | q4 | 86.6 | 86.60 | 86.6 | +0.000 | OK |
| `glm` | q4 | 84.9 | 84.89 | 84.9 | -0.010 | OK |
| `northmini` | q4 | 83.7 | 83.66 | 83.7 | -0.040 | OK |
| `qwen` | q4 | 83.0 | 83.01 | 83.0 | +0.010 | OK |
| `katdev` | iq4 | 82.2 | 82.19 | 82.2 | -0.010 | OK |
| `gpt-oss` | mxfp4 | 77.1 | 77.14 | 77.1 | +0.040 | OK |

## Per-config components

| Config | LB | n | cov | A | tools% (raw) | 1−tools | C | B | D/10 | decode | decode/137 | **Composite (R1 wts)** | **Composite (R2 wts)†** | comp (per-cfg D) | BCB-Hard | IFEval |
|---|:--:|--:|:--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| `ornith` q4 | * | 30 | 10/10 | 0.987 | 9% (8.70%) | 0.91 | 0.863 | 0.556 | 0.983 | 74.4 | 0.543 | **88.35** | **84.57†** | 88.35 | — | — |
| `gemma` q4 | * | 30 | 10/10 | 0.911 | 3% (3.08%) | 0.97 | 0.863 | 0.333 | 0.967 | 137.1 | 1.001 | **87.08** | **80.18†** | 87.08 | — | — |
| `qwopus` q5 | * | 30 | 10/10 | 0.994 | 3% (3.49%) | 0.97 | 0.863 | 0.389 | 0.883 | 63.5 | 0.464 | **87.03** | **80.68†** | 87.03 | — | — |
| `gemma` q5 |  | 30 | 10/10 | 0.911 | 2% (2.47%) | 0.98 | 0.863 | 0.445 | 0.967 | 92.2 | 0.673 | **86.81** | **80.88†** | 86.81 | — | — |
| `opus` q4 | * | 30 | 10/10 | 0.976 | 5% (5.50%) | 0.95 | 0.863 | 0.445 | 0.867 | 71.9 | 0.525 | **86.60** | **81.11†** | 85.76 | 0.300 ‡10/148 | 0.250 ‡20/541 ⚠ |
| `opus` q5 |  | 30 | 10/10 | 0.923 | 3% (2.94%) | 0.97 | 0.818 | 0.611 | 0.867 | 68.4 | 0.499 | **86.10** | **81.75†** | 86.93 | — | — |
| `glm` q4 | * | 30 | 10/10 | 0.916 | 3% (2.94%) | 0.97 | 0.879 | 0.445 | 0.883 | 58.0 | 0.423 | **84.89** | **79.19†** | 84.89 | — | — |
| `glm` q5 |  | 30 | 10/10 | 0.880 | 4% (3.67%) | 0.96 | 0.909 | 0.445 | 0.883 | 65.3 | 0.477 | **84.10** | **78.70†** | 84.10 | — | — |
| `northmini` q4 | * | 30 | 10/10 | 0.942 | 19% (19.32%) | 0.81 | 0.879 | 0.556 | 0.958 | 57.9 | 0.423 | **83.66** | **81.47†** | 83.58 | — | — |
| `qwen` q5 |  | 30 | 10/10 | 0.970 | 28% (27.78%) | 0.72 | 0.863 | 0.556 | 0.975 | 92.6 | 0.676 | **83.58** | **82.66†** | 83.67 | — | — |
| `qwen` q4 | * | 30 | 10/10 | 0.991 | 32% (32.48%) | 0.68 | 0.894 | 0.500 | 0.975 | 86.8 | 0.634 | **83.01** | **82.28†** | 82.93 | — | — |
| `katdev` iq4 | * | 30 | 10/10 | 0.946 | 5% (4.60%) | 0.95 | 0.863 | 0.278 | 0.908 | 14.2 | 0.104 | **82.19** | **75.03†** | 82.10 | — | — |
| `katdev` q4 |  | 30 | 10/10 | 0.885 | 2% (2.42%) | 0.98 | 0.863 | 0.333 | 0.908 | 13.4 | 0.098 | **81.32** | **74.27†** | 81.41 | — | — |
| `northmini` q5 |  | 30 | 10/10 | 0.898 | 18% (17.86%) | 0.82 | 0.803 | 0.444 | 0.958 | 55.3 | 0.404 | **80.02** | **76.17†** | 80.10 | — | — |
| `gpt-oss` mxfp4 | * | 30 | 10/10 | 0.883 | 11% (10.53%) | 0.89 | 0.863 | 0.111 | 0.883 | 30.1 | 0.220 | **77.14** | **69.22†** | 77.14 | — | — |

`*` = the config the published leaderboard uses for this model's headline composite. `†` = round-2 weights (docs/methodology.md §6.11) -- **not the same quantity as the round-1-weighted composite to its left**; see the caveat at the top of this document and the reweighting-impact table below before comparing the two columns as a ranking. `cov` = tasks with units / tasks the selected set defines; **`‡` = PARTIAL — both composites on that row were computed over only those tasks**, per-suite breakdown in the coverage section below. In the **BCB-Hard / IFEval** columns `‡n/m` carries the same warning for the external lane — that score was measured over n of the benchmark's m items (`?` = the artifact records no denominator at all), so it is a slice score and **not comparable to a full-set number**; `⚠` = contaminated, see the round-2 axes section below.

### Coverage — which rows rest on the whole task set, and which do not

All 15 configs have units on every one of the 10 tasks in the selected set. Every composite above covers the full set.

## Reweighting impact — round-1 vs round-2 weights, same underlying scores

Isolates the weight change from any task-set change: both composites below are computed from the *same* per-axis scores (this is `--round 1`), differing only in which weights combine them. Restricted to each model's headline (published-leaderboard) config.

| Rank (R1 wts) | Model | Quant | Composite (R1 wts) | Composite (R2 wts) | Rank (R2 wts) | ΔRank |
|--:|---|---|--:|--:|--:|:--:|
| 1 | `ornith` | q4 | 88.35 | 84.57 | 1 | → 0 |
| 2 | `gemma` | q4 | 87.08 | 80.18 | 6 | ↓ 4 |
| 3 | `qwopus` | q5 | 87.03 | 80.68 | 5 | ↓ 2 |
| 4 | `opus` | q4 | 86.60 | 81.11 | 4 | → 0 |
| 5 | `glm` | q4 | 84.89 | 79.19 | 7 | ↓ 2 |
| 6 | `northmini` | q4 | 83.66 | 81.47 | 3 | ↑ 3 |
| 7 | `qwen` | q4 | 83.01 | 82.28 | 2 | ↑ 5 |
| 8 | `katdev` | iq4 | 82.19 | 75.03 | 8 | → 0 |
| 9 | `gpt-oss` | mxfp4 | 77.14 | 69.22 | 9 | → 0 |

**Reweighting alone DOES reorder the fleet.**

> **Why the reweight:** tool_malformed drops 0.25->0.10 because the round-1 distribution is BIMODAL, not saturated: ten configs cluster at 2.4-5.5% malformed, where the ordinal differences are ~3 vs ~5 malformed calls out of ~100 -- noise, not signal -- while ornith (8.7%), gpt-oss (10.5%), northmini (17.9-19.3%) and qwen (27.8-32.5%) are 2-10x worse and already get punished decisively even at a small weight. A quarter of the score should not ride on noise inside the tight cluster. The freed 0.15 follows spread: B_recall ran 0.111-0.611 in round 1 (the healthiest, least-saturated axis) -> +0.10; C_edit ran 0.803-0.909 (narrow, but not as saturated as A_coding was) -> +0.05.

## Round-2 axes (reported alongside, UNWEIGHTED)

| Config | bcb_hard_pass@1 | tasks scored | ifeval_prompt_strict | prompts scored |
|---|--:|:--:|--:|:--:|
| `opus__q4` | 0.300 ‡10/148 | 10/148 PARTIAL | 0.250 ‡20/541 ⚠ | 20/541 PARTIAL |

**2 of these numbers do not cover their benchmark's full set, or do not cover it cleanly.** A slice score is useful while a run is in progress; it is not a leaderboard number and it is not comparable to a config measured over a different slice.

- **`opus__q4` · bcb_hard_pass@1 = 0.300** — PARTIAL — 10/148 tasks scored; a slice score, NOT comparable to a full-set number nor to another config measured over a different slice.
  Full-set size from fallback constant BCB_HARD_N_TASKS=148 — this benchmark's artifact records no available-count field. Source `bcb__opus__q4.json`, ts `2026-07-26T21:25:45.990529+00:00`.
- **`opus__q4` · ifeval_prompt_strict = 0.250** — PARTIAL — 20/541 prompts scored; a slice score, NOT comparable to a full-set number nor to another config measured over a different slice.
  Full-set size from fallback constant IFEVAL_N_PROMPTS_FULL=541 — the artifact carries no `n_prompts_available`. Source `ifeval__opus__q4.json`, ts `2026-07-25T20:41:30.738149+00:00`.
  **⚠ n_finish_length=15 of 20 prompts — CONTAMINATED, not merely partial: 15 of 20 prompts hit the max_tokens ceiling without finishing and were scored anyway — for a config whose reasoning carries no `<think>` tag the stripper cannot fire, so that prose was graded as the answer (eval/ROUND2_STATUS.md, 'A second leak shape': 13 of opus/q4's 15). Detection only; nothing is re-scored here.**

> bcb_hard_pass@1 and ifeval_prompt_strict are reported UNWEIGHTED and are NOT part of the composite. Re-weighting waits for evidence of correlation.

> **Coverage:** Per config and per external axis: the value, `n_measured` (the denominator that run actually scored -- `n_tasks` for BigCodeBench, `n_prompts` for IFEval) against `n_full_set` (148 Hard tasks / 541 IFEval prompts), where that full-set size came from, the artifact's `ts` and its filename. Same argument as `coverage`, applied to the external lane: 0.3 over a 10-task probe and 0.3 over the full 148 are the same float and not the same claim, and both shapes are on disk. A missing denominator field yields status UNKNOWN -- silence must never render as full coverage. Slice scores are NOT comparable to full-set scores, nor to each other across different slices. `truncation_contamination` (IFEval only) is a separate and stronger warning than partial coverage: `n_finish_length > 0` means some scored prompts hit the token ceiling without finishing, and for a config whose reasoning carries no `<think>` tag the scorer graded that prose as the answer (eval/ROUND2_STATUS.md, 'A second leak shape'). Detection only -- no value is adjusted, suppressed or re-scored here.

## Term conventions (what each symbol in the formula actually means here)

- **`a_coding`** — Unweighted mean of grade.pass_rate over every A_coding unit of the config in the selected task set (12 units in round 1 = 4 tasks x 3 reps), rounded to 3 dp.
- **`c_edit`** — Unweighted mean of grade.pytest.pass_rate over C_edit units -- the pytest pass-rate, NOT diff.surgical_score (methodology.md §3 Normalization: 'A/C report pytest pass-rate'). surgical_score is reported as a diagnostic column only.
- **`b_recall`** — Unweighted mean of grade.recall over B_review units.
- **`tool_malformed_pct`** — sum(driver.tool_calls.malformed) / sum(driver.tool_calls.total) over ALL units of the config in the selected task set (all four suites, not just A), then ROUNDED TO THE NEAREST WHOLE PERCENT. The rounding is required to reproduce the published table: with the raw rate, ornith computes 88.42 against a published 88.3. methodology.md does not state the rounding -- this is an inferred convention. OPEN QUESTION (see eval/ROUND2_STATUS.md 'Needs Denis'), behavior as-implemented TODAY: this is RECOMPUTED FROM SCRATCH per --round selection, never the round-1 value carried forward. --round 1 sums malformed/total over round-1-task units only; --round 2 sums over round-2-task units only (round-1 units EXCLUDED from that sum); --round all sums over round-1 AND round-2 units COMBINED. A config's tool_malformed_pct can therefore differ across --round 1 / 2 / all even with zero new units of its own, because the denominator changes. Whether this is the right policy (vs. e.g. holding the round-1 rate fixed and only reporting round-2-task tool reliability as a separate column) is undecided and belongs to Denis, not to this script.
- **`d_text`** — Mean 0-10 judge score from DTEXT_JUDGED.json, POOLED ACROSS BOTH QUANTS OF THE MODEL (12 judged units), divided by 10. methodology.md says the composite uses the q4 quant, but the D term in the published table is model-level: per-config D gives opus 85.8 against a published 86.6. Per-config D is reported alongside as d_text_config and drives the diagnostic composite_config_d column.
- **`decode`** — Median decode_tps over all cold_samples + warm_samples of every point in probe__<model>__<quant>.json (same reduction as digest.py), divided by 137. Not task-scoped, so it is identical for --round 1 / 2 / all. gemma-q4's 137.1 makes its term marginally exceed 1.0; the formula is applied verbatim, uncapped.
- **`leaderboard_quant`** — q4 for every multi-quant model EXCEPT katdev, which reproduces only from iq4. qwopus (q5), ornith (q4) and gpt-oss (mxfp4) are single-quant.
- **`external_axes`** — bcb_hard_pass@1 and ifeval_prompt_strict are reported UNWEIGHTED and are NOT part of the composite. Re-weighting waits for evidence of correlation.
- **`external_coverage`** — Per config and per external axis: the value, `n_measured` (the denominator that run actually scored -- `n_tasks` for BigCodeBench, `n_prompts` for IFEval) against `n_full_set` (148 Hard tasks / 541 IFEval prompts), where that full-set size came from, the artifact's `ts` and its filename. Same argument as `coverage`, applied to the external lane: 0.3 over a 10-task probe and 0.3 over the full 148 are the same float and not the same claim, and both shapes are on disk. A missing denominator field yields status UNKNOWN -- silence must never render as full coverage. Slice scores are NOT comparable to full-set scores, nor to each other across different slices. `truncation_contamination` (IFEval only) is a separate and stronger warning than partial coverage: `n_finish_length > 0` means some scored prompts hit the token ceiling without finishing, and for a config whose reasoning carries no `<think>` tag the scorer graded that prose as the answer (eval/ROUND2_STATUS.md, 'A second leak shape'). Detection only -- no value is adjusted, suppressed or re-scored here.
- **`coverage`** — Per config: how many tasks OF THE SELECTED TASK SET this config actually has units on disk for (`tasks_with_units`) against how many that set defines (`tasks_in_set`), overall and broken down per suite. A task counts as covered if at least one unit file for it parsed -- reps are NOT checked, so 1/3 reps still counts the task as covered and the composite is a thinner mean than a complete row's. `composite_coverage` repeats the verdict (`complete` / `PARTIAL n/m ...`) next to the composite itself. This is deliberately NOT the same thing as `missing_terms`, which is per-AXIS: a config with only round-1 units under --round all has data on every axis, so missing_terms is [] while its composite covers 10 of 31 tasks. Coverage is never a reason to null the composite -- a partial number is useful mid-run, it just may not claim to be a complete one.
