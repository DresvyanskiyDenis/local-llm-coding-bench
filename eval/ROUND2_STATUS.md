# Round 2 — build status

*Session of 2026-07-25/26, branch `feature/round2-expansion`. Live document: it is written as the
phases land, so a usage-limit stop leaves an honest record rather than a silence.*

Gate definitions are [`IMPLEMENTATION_PLAN.md` §9](IMPLEMENTATION_PLAN.md#9-execution-order-for-the-night).

## Phase status

| # | Phase | Gate | Status |
|---|---|---|---|
| 0 | vendor + venvs + env_health + reasoning leak | sha256s recorded, `env_health.json` written, leak answer recorded | 🟡 in flight |
| 1 | IFEval adapter | `--limit 20` scores one config, four metrics populated | 🟡 in flight |
| 2 | BigCodeBench adapter | `--limit 10` gives `pass@1` with `n_env_errors == 0`, wall-clock recorded | 🟡 in flight |
| 3 | grader changes | round-1 fixtures re-grade byte-identically; control returns `recall: null` | 🟡 in flight |
| 5 | pairwise judge | runs end-to-end on round-1 D answers; order effect estimated | 🟡 in flight |
| 6 | `aggregate.py` | reproduces the **existing** `docs/leaderboard.md` composite from result files | 🟡 in flight |
| 4 | 11 new task dirs | each B bug proven by `verify_bugs.py`; C ref solutions pass; D token counts measured | ⬜ not started (last on purpose) |

## Environment health

_pending — Phase 0._

## Reasoning leak

_pending — Phase 0 step 6._

## Measured wall-clock

_pending — Phases 1 and 2._

## Needs Denis

_none recorded yet._

## Blockers

_none recorded yet._
