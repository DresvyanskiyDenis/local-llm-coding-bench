# Rank-correlation validation — round-1 composite vs externally-authored graders

*Generated 2026-07-25T20:21:05.680047+00:00 by `eval/harness/validate_correlation.py` from `AGGREGATE.json` (round 1, 15 configs, scope `all`).*

## Result: nothing to correlate yet

No externally-graded result files cover enough configs (n >= 3 required). The round-1 side is ready; the external side is not.

## External rankings available

| Ranking | n configs | Source | Status |
|---|--:|---|---|
| `bcb_hard_pass@1` | 0 | `eval/results/bcb__<model>__<quant>.json` | No bcb__*.json result files on disk yet. |
| `ifeval_prompt_strict` | 0 | `eval/results/ifeval__<model>__<quant>.json` | No ifeval__*.json result files on disk yet. |
| `dtext_bt_strength` | 0 | `eval/results/DTEXT_PAIRWISE.json` | DTEXT_PAIRWISE.json not present. |

## Spearman rho — internal axis vs external ranking

| External ranking | Internal axis | n | rho | p (permutation) | p method | p (t, ref only) |
|---|---|--:|--:|--:|---|--:|
| `bcb_hard_pass@1` | `composite` | 0 | — | — | n=0: nothing to correlate yet — No bcb__*.json result files on disk yet. | — |
| `bcb_hard_pass@1` | `a_coding` | 0 | — | — | n=0: nothing to correlate yet — No bcb__*.json result files on disk yet. | — |
| `bcb_hard_pass@1` | `tool_reliability` | 0 | — | — | n=0: nothing to correlate yet — No bcb__*.json result files on disk yet. | — |
| `bcb_hard_pass@1` | `c_edit` | 0 | — | — | n=0: nothing to correlate yet — No bcb__*.json result files on disk yet. | — |
| `bcb_hard_pass@1` | `b_recall` | 0 | — | — | n=0: nothing to correlate yet — No bcb__*.json result files on disk yet. | — |
| `bcb_hard_pass@1` | `d_text` | 0 | — | — | n=0: nothing to correlate yet — No bcb__*.json result files on disk yet. | — |
| `bcb_hard_pass@1` | `decode` | 0 | — | — | n=0: nothing to correlate yet — No bcb__*.json result files on disk yet. | — |
| `ifeval_prompt_strict` | `composite` | 0 | — | — | n=0: nothing to correlate yet — No ifeval__*.json result files on disk yet. | — |
| `ifeval_prompt_strict` | `a_coding` | 0 | — | — | n=0: nothing to correlate yet — No ifeval__*.json result files on disk yet. | — |
| `ifeval_prompt_strict` | `tool_reliability` | 0 | — | — | n=0: nothing to correlate yet — No ifeval__*.json result files on disk yet. | — |
| `ifeval_prompt_strict` | `c_edit` | 0 | — | — | n=0: nothing to correlate yet — No ifeval__*.json result files on disk yet. | — |
| `ifeval_prompt_strict` | `b_recall` | 0 | — | — | n=0: nothing to correlate yet — No ifeval__*.json result files on disk yet. | — |
| `ifeval_prompt_strict` | `d_text` | 0 | — | — | n=0: nothing to correlate yet — No ifeval__*.json result files on disk yet. | — |
| `ifeval_prompt_strict` | `decode` | 0 | — | — | n=0: nothing to correlate yet — No ifeval__*.json result files on disk yet. | — |
| `dtext_bt_strength` | `composite` | 0 | — | — | n=0: nothing to correlate yet — DTEXT_PAIRWISE.json not present. | — |
| `dtext_bt_strength` | `a_coding` | 0 | — | — | n=0: nothing to correlate yet — DTEXT_PAIRWISE.json not present. | — |
| `dtext_bt_strength` | `tool_reliability` | 0 | — | — | n=0: nothing to correlate yet — DTEXT_PAIRWISE.json not present. | — |
| `dtext_bt_strength` | `c_edit` | 0 | — | — | n=0: nothing to correlate yet — DTEXT_PAIRWISE.json not present. | — |
| `dtext_bt_strength` | `b_recall` | 0 | — | — | n=0: nothing to correlate yet — DTEXT_PAIRWISE.json not present. | — |
| `dtext_bt_strength` | `d_text` | 0 | — | — | n=0: nothing to correlate yet — DTEXT_PAIRWISE.json not present. | — |
| `dtext_bt_strength` | `decode` | 0 | — | — | n=0: nothing to correlate yet — DTEXT_PAIRWISE.json not present. | — |

`p (permutation)` is the reported p-value. `p (t, ref only)` is the Student-t approximation, shown for comparison and NOT to be quoted — at n <= 15 it is systematically anti-conservative (e.g. n=5 rho=+0.821: exact 0.133 vs t 0.089).

## Comparability caveats — these travel with the numbers

- **quantization_and_checkpoint** — Published leaderboard numbers for these model families are BF16 vendor checkpoints. This fleet runs Q4/Q5/IQ4 GGUF quantizations, and several configs are community fine-tunes with no public leaderboard entry at all. A rank correlation computed here is between THIS fleet's internal axes and THIS fleet's externally-graded scores -- it is not a claim that the local quantized model reproduces the vendor checkpoint's public score.
- **bcb_within_fleet_only** — BigCodeBench-Hard here runs under a RELAXED-PIN LOCAL executor (eval/IMPLEMENTATION_PLAN.md §1: numpy/numba/keras/gensim pins from requirements-eval.txt have no Apple-Silicon wheels and were installed unpinned). Every config executes under the identical executor, so the WITHIN-FLEET RANKING -- which is exactly what Spearman consumes -- holds. The absolute pass@1 does NOT, and must never be quoted against the public BigCodeBench leaderboard.
- **harness_level_vs_model_level** — Round-1 axes are HARNESS-level: model + OpenCode agent + tools + graders. IFEval and BCB-Hard are MODEL-level: single-turn, no agent, no tools. A divergence between them may therefore be a harness effect rather than a model effect. That is a finding, but only if the two levels are never conflated.
- **statistical_power** — n <= 15 configs, and the configs are not independent (two quants of the same model share a checkpoint). Confidence intervals on rho are wide and p-values should be read as weak evidence at best. A non-significant result at this n is NOT evidence of no correlation.
