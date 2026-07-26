# Phase 4 task verification

`33/33` checks passed. Regenerate: `uv run eval/harness/ops/verify_phase4.py`.

| Area | Task | Check | Verdict | Number |
|---|---|---|---|---|
| B | `B6_control_nobugs` | key.json plants zero bugs | PASS | 0 bugs |
| B | `B6_control_nobugs` | recall is literal JSON null (clean) | PASS | recall=null |
| B | `B6_control_nobugs` | precision inverts correctly (clean) | PASS | precision=1.0, fpr=0.0 |
| B | `B6_control_nobugs` | recall is literal JSON null (hallucinated) | PASS | recall=null |
| B | `B6_control_nobugs` | precision inverts correctly (hallucinated) | PASS | precision=0.0, fpr=1.0 |
| B | `B6_control_nobugs` | digest.py mean drops null (would drag if 0.0) | PASS | null->0.834 vs 0.0->0.556 |
| B | `B3_concurrency_ledger` | verify_bugs.py: declared vs demonstrated | PASS | 3/3 demonstrated |
| B | `B3_concurrency_ledger` | key.json line ranges inside the file | PASS | 3/3 in range |
| B | `B3_concurrency_ledger` | review_grader round-trip (competent answer) | PASS | recall=1.0, precision=1.0, halluc=0 |
| B | `B4_io_encoding` | verify_bugs.py: declared vs demonstrated | PASS | 3/3 demonstrated |
| B | `B4_io_encoding` | key.json line ranges inside the file | PASS | 3/3 in range |
| B | `B4_io_encoding` | review_grader round-trip (competent answer) | PASS | recall=1.0, precision=1.0, halluc=0 |
| B | `B5_temporal_money` | verify_bugs.py: declared vs demonstrated | PASS | 3/3 demonstrated |
| B | `B5_temporal_money` | key.json line ranges inside the file | PASS | 3/3 in range |
| B | `B5_temporal_money` | review_grader round-trip (competent answer) | PASS | recall=1.0, precision=1.0, halluc=0 |
| C | `C3_scope_creep` | PASS case clean, changed lines vs FREE_LINES=15 | PASS | 8 lines (limit 15), surgical=1.0, pytest=1.0 |
| C | `C3_scope_creep` | FAIL case: trap fires | PASS | acted_on=True, surgical=0.7, pytest=1.0 |
| C | `C4_already_done` | PASS case clean, changed lines vs FREE_LINES=15 | PASS | 6 lines (limit 15), surgical=1.0, pytest=1.0 |
| C | `C4_already_done` | FAIL case: trap fires | PASS | acted_on=True, surgical=0.7, pytest=1.0 |
| C | `C4_already_done` | EMPTY diff reads as restraint on diff side | PASS | changed=0, surgical=1.0 (NOT a failure to respond) |
| C | `C4_already_done` | EMPTY diff separated from correct answer by pytest half<br>_diff_grader ALONE cannot tell them apart (both surgical=1.0)_ | PASS | pytest=0.583 (7/12) vs 1.0 for the correct edit |
| C | `C5_contradiction` | PASS case clean, changed lines vs FREE_LINES=15 | PASS | 6 lines (limit 15), surgical=1.0, pytest=1.0 |
| C | `C5_contradiction` | FAIL case: trap fires | PASS | acted_on=True, surgical=0.7, pytest=0.917 |
| C | `C5_contradiction` | contradiction signal: named vs silent (documented false-negative)<br>_keyword match only -- cannot tell 'right for the right reason, unstated' from 'never noticed'_ | PASS | named=True, silent=False (both code-correct: acted_on=False) |
| D | `longctx_core` | assembled core.md sha256 matches manifest | PASS | 8703a2d4bd7f7051... |
| D | `manifest.core` | on-disk core source sha256s | PASS | 3/3 OK |
| D | `manifest.core` | core.md == sources joined by blank line | PASS | 36396 == 36396 bytes |
| D | `manifest.padding` | fetched padding sha256s (re-fetched from pinned commits) | PASS | 49/49 OK |
| D | `longctx_manifest` | total sha256 refs verified | PASS | 53/53 |
| D | `D3/D4/D5` | core present in full in all three corpora | PASS | D3=610/610, D4=610/610, D5=610/610 |
| D | `D3/D4/D5` | extracted core byte-identical across the ladder | PASS | 92009e4649a9b08d... x3, fragments=[14, 19, 19] |
| D | `D3/D4/D5` | PROMPT/rubric/key_points identical + match longctx_shared | PASS | 3/3 identical |
| D | `D3/D4/D5` | rep count held constant across the ladder<br>_D3 falls through to orchestrate.py default_reps=[1,2,3]; D4/D5 pinned to 1_ | PASS | D3=[1]; D4=[1]; D5=[1] |
