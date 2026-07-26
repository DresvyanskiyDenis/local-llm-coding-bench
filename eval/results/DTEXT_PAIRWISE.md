# D_text pairwise judge — Bradley-Terry re-ranking

- Generated: 2026-07-26T20:28:36.035134+00:00
- Suite/round: D_text / round 1
- Judge: claude -p --model sonnet (minimal context: --strict-mcp-config --disable-slash-commands --tools '')
- Seed: 42
- schema_version: 2

## Input inventory

- (config, task) pairs expected: 30
- (config, task) pairs with real answer text found: 30
- missing: 0

> ## :warning: PARTIAL PASS — NOT THE FULL DESIGN
> **76 of 210** designed pairs judged (134 remain). Every BT strength, order-effect estimate, and Spearman correlation in this document is fitted on this partial pass only. Do not read any ranking below as final. The remainder is cache-resumable and awaits explicit authorization to run.
>
> | task | judged | designed |
> |---|---|---|
> | D1_summarize_mtp | 46 | 105 |
> | D2_dedup_approaches | 30 | 105 |


## Run budget

- real judge calls made: 0
- cache hits: 76
- genuine unparseable verdicts (judge ran, bad output): 0
- backend errors (judge never ran — rate limit/timeout/nonzero exit): 0
- skipped (limit reached): 134
- limit applied: 0

**Usage-limit tokens consumed THIS invocation** (the scarce resource — this account runs on a Pro subscription, so `cost_usd` stored per-pair is a notional API price, not money spent):

- cache creation: 0
- cache read: 0
- input: 0
- output: 0
- (usage-limit tokens for NEW live calls only this invocation (cache hits and backend errors consume none). total_cost_usd stored per-pair is a notional API price, not money spent — this account runs on a Pro subscription.)

## D1_summarize_mtp

- pairing scheme: **roundrobin**
- pairs designed: 105 · attempted: 105 · judged (real verdict, non-skipped): 46 · skipped (missing answer): 0 · unparseable: 0 · backend errors: 0

**Order (position) effect** — first-shown win-rate over decisive (non-tie, parseable, non-backend-error) judgements, Wilson score 95% CI
- first-position win rate: 0.32608695652173914 (95% CI [0.20865764564493355, 0.4703253725567292], n=46 decisive, 0 ties, 0 unparseable, 0 backend errors)
- significant bias vs 0.5: **True**

**Bradley-Terry strengths** (geometric-mean-normalized to 1; 95% CI via 1000-resample bootstrap over games)

> :warning: 4/15 configs are `low_confidence` (< 4 judged games) in this partial pass — their strength is an anecdotal point estimate, not a fitted rank, and its 95% CI is correspondingly wide/unreliable.

| config | strength | 95% CI | n_games | low_confidence | insufficient data |
|---|---|---|---|---|---|
| qwen__q5 | 552.9640 | [1.0, 4101.412676492597] | 3 | True | False |
| qwen__q4 | 552.9640 | [1.0, 3629.035353934396] | 3 | True | False |
| ornith__q4 | 552.9640 | [1.0, 4664.251304840749] | 3 | True | False |
| opus__q4 | 0.8906 | [0.0, 2087.742484930913] | 4 | False | False |
| glm__q5 | 0.7056 | [0.03690441386896159, 1238.9578739379324] | 10 | False | False |
| glm__q4 | 0.4309 | [0.011846165071407039, 57.04547447523431] | 14 | False | False |
| opus__q5 | 0.2473 | [0.0, 543.380680942158] | 4 | False | False |
| northmini__q5 | 0.2473 | [0.0, 120.57238163377737] | 4 | False | False |
| gemma__q5 | 0.1699 | [0.00013831790903934575, 2.0411297256709613] | 14 | False | False |
| qwopus__q5 | 0.0779 | [0.0, 1139.5618754278455] | 3 | True | False |
| gemma__q4 | 0.0685 | [2.124071792317414e-07, 0.30929624127439814] | 14 | False | False |
| northmini__q4 | 0.0671 | [0.0, 3.1325912190076743] | 4 | False | False |
| gpt-oss__mxfp4 | 0.0671 | [0.0, 551.7271149400626] | 4 | False | False |
| katdev__iq4 | 0.0671 | [0.0, 3.7641279450686675] | 4 | False | False |
| katdev__q4 | 0.0000 | [0.0, 0.0] | 4 | False | False |

**Spearman vs. round-1 absolute 0-10 judging (DTEXT_JUDGED.json)**
- rho = 0.36790019366204957, p = 0.1775911204439778, n = 15 (median 4.0 games/config) (permutation, 20000 draws, seed=42)

**Win matrix** (row beat column; ties = 0.5 each side)

```
         gemma__q4  gemma__q5    glm__q4    glm__q5 gpt-oss__m katdev__iq katdev__q4 northmini_ northmini_   opus__q4   opus__q5 ornith__q4   qwen__q4   qwen__q5 qwopus__q5
gemma__q4        0.0        0.0        0.0        0.0        1.0        1.0        1.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0        1.0
gemma__q5        1.0        0.0        0.0        0.0        1.0        0.0        1.0        1.0        0.0        0.0        1.0        0.0        0.0        0.0        1.0
 glm__q4        1.0        1.0        0.0        1.0        1.0        1.0        1.0        1.0        1.0        0.0        0.0        0.0        0.0        0.0        0.0
 glm__q5        1.0        1.0        0.0        0.0        0.0        1.0        1.0        1.0        1.0        1.0        1.0        0.0        0.0        0.0        0.0
gpt-oss__m        0.0        0.0        0.0        1.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0
katdev__iq        0.0        1.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0
katdev__q4        0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0
northmini_        1.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0
northmini_        1.0        1.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0
opus__q4        1.0        1.0        1.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0
opus__q5        1.0        0.0        1.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0
ornith__q4        1.0        1.0        1.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0
qwen__q4        1.0        1.0        1.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0
qwen__q5        1.0        1.0        1.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0
qwopus__q5        0.0        0.0        1.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0
```

## D2_dedup_approaches

- pairing scheme: **roundrobin**
- pairs designed: 105 · attempted: 105 · judged (real verdict, non-skipped): 30 · skipped (missing answer): 0 · unparseable: 0 · backend errors: 0

**Order (position) effect** — first-shown win-rate over decisive (non-tie, parseable, non-backend-error) judgements, Wilson score 95% CI
- first-position win rate: 0.4666666666666667 (95% CI [0.3023212722412823, 0.6385798671847496], n=30 decisive, 0 ties, 0 unparseable, 0 backend errors)
- significant bias vs 0.5: **False**

**Bradley-Terry strengths** (geometric-mean-normalized to 1; 95% CI via 1000-resample bootstrap over games)

> :warning: 12/15 configs are `low_confidence` (< 4 judged games) in this partial pass — their strength is an anecdotal point estimate, not a fitted rank, and its 95% CI is correspondingly wide/unreliable.

| config | strength | 95% CI | n_games | low_confidence | insufficient data |
|---|---|---|---|---|---|
| qwen__q5 | 495.7318 | [1.0, 1284.1710368028905] | 2 | True | False |
| qwen__q4 | 495.7318 | [1.0, 1064.4736644697778] | 2 | True | False |
| opus__q5 | 495.7318 | [1.0, 1060.7393631795421] | 2 | True | False |
| opus__q4 | 495.7318 | [1.0, 1181.1515148370297] | 2 | True | False |
| northmini__q4 | 495.7318 | [1.0, 1285.9337690992954] | 2 | True | False |
| qwopus__q5 | 495.7318 | [1.0, 1103.7587317177586] | 2 | True | False |
| ornith__q4 | 495.7318 | [1.0, 1038.3574537298632] | 2 | True | False |
| gpt-oss__mxfp4 | 330.2121 | [1.0, 940.078148459684] | 3 | True | False |
| gemma__q4 | 0.4465 | [0.006733350451707602, 8.000213755066552] | 14 | False | False |
| northmini__q5 | 0.0016 | [0.0, 18.69176457651715] | 2 | True | False |
| katdev__q4 | 0.0016 | [0.0, 19.009986651882716] | 2 | True | False |
| gemma__q5 | 0.0000 | [0.0, 0.028580880463511878] | 14 | False | False |
| glm__q5 | 0.0000 | [0.0, 2.0] | 3 | True | False |
| katdev__iq4 | 0.0000 | [0.0, 2.0] | 3 | True | False |
| glm__q4 | 0.0000 | [0.0, 0.0] | 5 | False | False |

**Spearman vs. round-1 absolute 0-10 judging: NOT computed (not meaningful yet)**
- reason: NOT COMPUTED — median per-config coverage in this pass is only 2.0 judged games (< 4 threshold for a stable BT point estimate). A rho fitted on this would mostly reflect single-game sample noise, not true rank agreement with round-1 absolute scores.
- estimated pairs needed for a meaningful estimate: ~30 judged pairs (this task currently has 30)

**Win matrix** (row beat column; ties = 0.5 each side)

```
         gemma__q4  gemma__q5    glm__q4    glm__q5 gpt-oss__m katdev__iq katdev__q4 northmini_ northmini_   opus__q4   opus__q5 ornith__q4   qwen__q4   qwen__q5 qwopus__q5
gemma__q4        0.0        1.0        1.0        1.0        0.0        1.0        1.0        0.0        1.0        0.0        0.0        0.0        0.0        0.0        0.0
gemma__q5        0.0        0.0        1.0        1.0        0.0        1.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0
 glm__q4        0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0
 glm__q5        0.0        0.0        1.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0
gpt-oss__m        1.0        1.0        1.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0
katdev__iq        0.0        0.0        1.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0
katdev__q4        0.0        1.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0
northmini_        1.0        1.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0
northmini_        0.0        1.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0
opus__q4        1.0        1.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0
opus__q5        1.0        1.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0
ornith__q4        1.0        1.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0
qwen__q4        1.0        1.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0
qwen__q5        1.0        1.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0
qwopus__q5        1.0        1.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0        0.0
```

## Notes

- PARTIAL RUN — see top-level `partial_run`. PARTIAL PASS: 76 of 210 designed pairs judged across 2 task(s) (134 pairs remain). All BT strengths, order-effect estimates, and Spearman correlations below are fitted on this partial pass ONLY — they are not the full round-robin design and must not be read as final rankings. Already-judged pairs are permanently cache-resumable at $0 (use --limit 0 to refresh this report against the cache with guaranteed zero new spend); re-running with the same nonzero --limit is NOT a no-op — it will additionally spend on up to --limit new pairs per task. The remainder awaits Denis's explicit authorization to run.
- Round-1 D tasks (D1, D2) use full round-robin so they are directly comparable to the round-1 absolute judging (same method decided in IMPLEMENTATION_PLAN.md §7). D3-D6 (not authored yet this session) would use 8-round Swiss per the same plan.
- Position bias is measured from the per-pair randomized presentation order (fixed seed, independently randomized per pair) — see order_effect per task. If significant_bias is true, the plan's prescribed fix is a swap-and-rejudge pass (judge each pair in both orders and combine), not yet run by default this session.
- Bradley-Terry via MM iteration (Hunter 2004), plain numpy. 95% CIs via 1000-resample bootstrap over individual judged games.
- Spearman rho computed on ranks (average-rank tie handling) with a permutation p-value (20000 draws) — no scipy dependency.
- Budget tracking: this account runs on a Pro subscription — total_cost_usd stored per-pair is a notional API price, not money spent. The scarce resource is the usage limit; see run_budget.tokens_this_run (cache_creation/cache_read/input/output) for NEW live-call consumption this invocation. Investigated whether each pair's ~11.5K cache-creation tokens (system prompt re-cached fresh every process) could instead be cache reads: `claude -p --resume <session_id>` DOES convert a prior call's cache_creation into this call's cache_read (proven: 2nd-turn cache_read exactly matched 1st-turn cache_creation in an isolated test). NOT adopted for the full 210-pair design because (a) sharing one session across pairs breaks the judge's blind, independent-per-pair assumption (accumulated transcript = contamination risk across comparisons — a methodology call for Denis, not a silent perf optimization), and (b) savings were unstable in this actively multi-agent repo: a 3rd-turn test still re-created 3.4K fresh tokens, most likely from per-turn dynamic context (git status) that keeps changing while other agents commit concurrently. `--bare` (which would strip that dynamic context) cannot be used here — it requires ANTHROPIC_API_KEY and this account authenticates via Pro-subscription OAuth.