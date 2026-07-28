# Phase 4 task verification

`32/32 checks passed, 0 failed, 1 skipped (not attempted, so not graded), 3 notes`. Regenerate: `uv run eval/harness/ops/verify_phase4.py --offline`.

Verdicts: **PASS**/**FAIL** are graded. **SKIP** is a check that deliberately did not run — it is not a failure and is not in the denominator. **NOTE** is an observation with no pass/fail meaning.

## Not verified by this run

- `manifest.padding` — fetched padding sha256s (kind=fetched, NOT on disk): 0/49 not attempted (--offline). these 49 refs have no on-disk copy, so only a re-fetch can verify them; NOT verified by this run. To verify: `uv run eval/harness/ops/verify_phase4.py` (no --offline, needs network)

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
| D | `manifest.core` | core source sha256s, as embedded in core.md<br>_pinned snapshots verified against the frozen corpus, not against the live repo_ | PASS | 3/3 OK |
| D | `manifest.core` | core.md == sources joined by blank line | PASS | 36396 == 36396 bytes |
| D | `manifest.core` | live repo copy of docs/methodology.md<br>_docs/methodology.md has changed in the repo since the corpus was pinned at 020e776; the corpus deliberately retains the pinned snapshot, so D3/D4/D5's measured token counts stay valid_ | NOTE | 14017 -> 40908 bytes |
| D | `manifest.core` | live repo copy of docs/leaderboard.md<br>_6860 bytes, still identical to the snapshot_ | NOTE | unchanged since pin |
| D | `manifest.core` | live repo copy of docs/replication.md<br>_15517 bytes, still identical to the snapshot_ | NOTE | unchanged since pin |
| D | `manifest.padding` | fetched padding sha256s (kind=fetched, NOT on disk)<br>_these 49 refs have no on-disk copy, so only a re-fetch can verify them; NOT verified by this run. To verify: `uv run eval/harness/ops/verify_phase4.py` (no --offline, needs network)_ | SKIP | 0/49 not attempted (--offline) |
| D | `longctx_manifest` | sha256 refs verified (of those verifiable offline)<br>_the on-disk corpus is fully verified; the fetched padding refs are not_ | PASS | 4/4 offline-verifiable; 49 of 53 not attempted |
| D | `D3/D4/D5` | core present in full in all three corpora | PASS | D3=610/610, D4=610/610, D5=610/610 |
| D | `D3/D4/D5` | extracted core byte-identical across the ladder | PASS | 92009e4649a9b08d... x3, fragments=[14, 19, 19] |
| D | `D3/D4/D5` | PROMPT/rubric/key_points identical + match longctx_shared | PASS | 3/3 identical |
| D | `D3/D4/D5` | rep count held constant across the ladder<br>_all three pin reps explicitly, so none falls through to orchestrate.py default_reps (D3's fall-through confound was fixed in 169a3c6)_ | PASS | D3=[1]; D4=[1]; D5=[1] |
