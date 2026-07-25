# AGGREGATE — round 1

*Generated 2026-07-25T20:21:05.210686+00:00 by `eval/harness/aggregate.py`. 450 units over 10 tasks found on disk (task set defines 10).*

```
Overall = 0.35*A_coding + 0.25*(1 - tool_malformed%) + 0.15*C_edit + 0.10*B_recall + 0.10*(D_text/10) + 0.05*(decode/137) -> x100
```

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

| Config | LB | n | A | tools% (raw) | 1−tools | C | B | D/10 | decode | decode/137 | **Composite** | comp (per-cfg D) | BCB-Hard | IFEval |
|---|:--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| `ornith` q4 | * | 30 | 0.987 | 9% (8.70%) | 0.91 | 0.863 | 0.556 | 0.983 | 74.4 | 0.543 | **88.35** | 88.35 | — | — |
| `gemma` q4 | * | 30 | 0.911 | 3% (3.08%) | 0.97 | 0.863 | 0.333 | 0.967 | 137.1 | 1.001 | **87.08** | 87.08 | — | — |
| `qwopus` q5 | * | 30 | 0.994 | 3% (3.49%) | 0.97 | 0.863 | 0.389 | 0.883 | 63.5 | 0.464 | **87.03** | 87.03 | — | — |
| `gemma` q5 |  | 30 | 0.911 | 2% (2.47%) | 0.98 | 0.863 | 0.445 | 0.967 | 92.2 | 0.673 | **86.81** | 86.81 | — | — |
| `opus` q4 | * | 30 | 0.976 | 5% (5.50%) | 0.95 | 0.863 | 0.445 | 0.867 | 71.9 | 0.525 | **86.60** | 85.76 | — | — |
| `opus` q5 |  | 30 | 0.923 | 3% (2.94%) | 0.97 | 0.818 | 0.611 | 0.867 | 68.4 | 0.499 | **86.10** | 86.93 | — | — |
| `glm` q4 | * | 30 | 0.916 | 3% (2.94%) | 0.97 | 0.879 | 0.445 | 0.883 | 58.0 | 0.423 | **84.89** | 84.89 | — | — |
| `glm` q5 |  | 30 | 0.880 | 4% (3.67%) | 0.96 | 0.909 | 0.445 | 0.883 | 65.3 | 0.477 | **84.10** | 84.10 | — | — |
| `northmini` q4 | * | 30 | 0.942 | 19% (19.32%) | 0.81 | 0.879 | 0.556 | 0.958 | 57.9 | 0.423 | **83.66** | 83.58 | — | — |
| `qwen` q5 |  | 30 | 0.970 | 28% (27.78%) | 0.72 | 0.863 | 0.556 | 0.975 | 92.6 | 0.676 | **83.58** | 83.67 | — | — |
| `qwen` q4 | * | 30 | 0.991 | 32% (32.48%) | 0.68 | 0.894 | 0.500 | 0.975 | 86.8 | 0.634 | **83.01** | 82.93 | — | — |
| `katdev` iq4 | * | 30 | 0.946 | 5% (4.60%) | 0.95 | 0.863 | 0.278 | 0.908 | 14.2 | 0.104 | **82.19** | 82.10 | — | — |
| `katdev` q4 |  | 30 | 0.885 | 2% (2.42%) | 0.98 | 0.863 | 0.333 | 0.908 | 13.4 | 0.098 | **81.32** | 81.41 | — | — |
| `northmini` q5 |  | 30 | 0.898 | 18% (17.86%) | 0.82 | 0.803 | 0.444 | 0.958 | 55.3 | 0.404 | **80.02** | 80.10 | — | — |
| `gpt-oss` mxfp4 | * | 30 | 0.883 | 11% (10.53%) | 0.89 | 0.863 | 0.111 | 0.883 | 30.1 | 0.220 | **77.14** | 77.14 | — | — |

`*` = the config the published leaderboard uses for this model's headline composite.

## Round-2 axes (reported alongside, UNWEIGHTED)

No `bcb__*.json` / `ifeval__*.json` result files on disk yet — both axes null.

> bcb_hard_pass@1 and ifeval_prompt_strict are reported UNWEIGHTED and are NOT part of the composite. Re-weighting waits for evidence of correlation.

## Term conventions (what each symbol in the formula actually means here)

- **`a_coding`** — Unweighted mean of grade.pass_rate over every A_coding unit of the config in the selected task set (12 units in round 1 = 4 tasks x 3 reps), rounded to 3 dp.
- **`c_edit`** — Unweighted mean of grade.pytest.pass_rate over C_edit units -- the pytest pass-rate, NOT diff.surgical_score (methodology.md §3 Normalization: 'A/C report pytest pass-rate'). surgical_score is reported as a diagnostic column only.
- **`b_recall`** — Unweighted mean of grade.recall over B_review units.
- **`tool_malformed_pct`** — sum(driver.tool_calls.malformed) / sum(driver.tool_calls.total) over ALL units of the config in the selected task set (all four suites, not just A), then ROUNDED TO THE NEAREST WHOLE PERCENT. The rounding is required to reproduce the published table: with the raw rate, ornith computes 88.42 against a published 88.3. methodology.md does not state the rounding -- this is an inferred convention.
- **`d_text`** — Mean 0-10 judge score from DTEXT_JUDGED.json, POOLED ACROSS BOTH QUANTS OF THE MODEL (12 judged units), divided by 10. methodology.md says the composite uses the q4 quant, but the D term in the published table is model-level: per-config D gives opus 85.8 against a published 86.6. Per-config D is reported alongside as d_text_config and drives the diagnostic composite_config_d column.
- **`decode`** — Median decode_tps over all cold_samples + warm_samples of every point in probe__<model>__<quant>.json (same reduction as digest.py), divided by 137. Not task-scoped, so it is identical for --round 1 / 2 / all. gemma-q4's 137.1 makes its term marginally exceed 1.0; the formula is applied verbatim, uncapped.
- **`leaderboard_quant`** — q4 for every multi-quant model EXCEPT katdev, which reproduces only from iq4. qwopus (q5), ornith (q4) and gpt-oss (mxfp4) are single-quant.
- **`external_axes`** — bcb_hard_pass@1 and ifeval_prompt_strict are reported UNWEIGHTED and are NOT part of the composite. Re-weighting waits for evidence of correlation.
