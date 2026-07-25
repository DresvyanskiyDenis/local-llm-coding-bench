# Round 2 — session kickoff prompt

*Paste the block below into a fresh Claude Code session started in
`~/MyProjects/local-llm-coding-bench`. Everything it needs is on disk; it should not need to ask
questions to start.*

---

```
Implement round 2 of this benchmark. Full spec: eval/IMPLEMENTATION_PLAN.md — read it first,
together with eval/experiments_expansion_plan.md (what and why) and eval/harness/CONTRACT.md
(interfaces). Do not re-derive the decisions in those documents; they are settled.

WHAT SUCCESS LOOKS LIKE
By the end of the session these four commands work and each has produced a real file:
  uv run eval/harness/orchestrate.py --dry-run                          # round-2 tasks discovered, all PASS
  uv run eval/external/ifeval/run_ifeval.py --only opus --limit 20      # -> results/ifeval__opus__q4.json
  uv run eval/external/bigcodebench/run_bcb.py --only opus --limit 10   # -> results/bcb__opus__q4.json
  uv run eval/harness/pairwise_judge.py --suite D_text --round 1        # -> results/DTEXT_PAIRWISE.json

DO NOT run the full 15-config evaluation. You are building the thing that runs it. Denis
launches the run himself.

ORDER — follow §9 of the plan exactly. It is ordered by blast radius, not by importance:
Phase 0 (vendor + venvs + env_health + reasoning-leak check) -> Phase 1 (IFEval) ->
Phase 2 (BigCodeBench) -> Phase 3 (graders) -> Phase 5 (pairwise judge) ->
Phase 6 (aggregate.py + validate_correlation.py + docs) -> Phase 4 (11 new task dirs) LAST.
Do not reorder. Phase 4 is last on purpose: everything before it is verifiable without a model,
and hand-authored tasks must not be rushed at 4am against a usage limit.

Each phase has a gate in §9. Do not start the next phase until the current gate passes. If a gate
fails, fix it or record the failure explicitly — never proceed past a red gate silently.

ALREADY DECIDED — do not re-litigate:
- BigCodeBench executor: relaxed-pin LOCAL execution. No Docker (RAM), no Gradio remote (upload).
  Consequence: BCB pass@1 is a within-fleet number, not comparable to the public leaderboard.
  Label it that way everywhere it appears.
- Serving: :8888 is currently held by llama-swap (since 2026-07-21), NOT unsloth-serve as in
  round 1. For an eval run llama-swap is STOPPED and unsloth-serve serves, exactly as round 1 did
  — this keeps all 15 configs (llama-swap is one quant per model id) and keeps the serving stack
  constant across rounds. Read §3.5 of the plan; it has three consequences and all three are
  build items: ops/serving_mode.sh, the clear_port() guard, and eval_proxy.py.
- IFEval: vendor the google-research verifier, do NOT use lm-evaluation-harness (torch is a core
  dependency there and is not wanted on this machine).
- Pairwise judge: `claude -p` via --judge-cmd. There is no ANTHROPIC_API_KEY on this machine.
- The composite is NOT re-weighted this round. BCB and IFEval are reported as unweighted new axes.

HARD RULES
- Branch feature/round2-expansion. Commit after EVERY phase, conventional commits. A usage-limit
  stop must leave a clean tree and a runnable repo, never a half-applied phase.
- eval/results/*.json from round 1 is IMMUTABLE. Round 2 writes new filenames only. If you find
  yourself editing a round-1 result file, stop — you have misunderstood something.
- orchestrate.py is additive-only. It survived three real overnight runs. Import from it
  (serve_config, unload, wait_for_ready, clear_port); do not refactor it. The one permitted
  change is the per-task reps/configs override in planned_units() specified in Phase 3.
- Vendored third-party code is UNMODIFIED, with PROVENANCE.md (URL + sha256 + date). Modifying a
  vendored grader forfeits the entire point of this round.
- uv / uv run only. Never pip, never poetry. Never /tmp — use $TMPDIR or the scratchpad.
- Every new script gets the PEP 723 inline header, per CONTRACT.md.

VERIFY, DO NOT ASSUME — these four have already burned this project once each:
- orchestrate.py's clear_port() SIGKILLs whatever holds :8888 on the premise that the engine owns
  the port exclusively. That premise is now false — it would silently kill llama-swap. Guard it
  (fail loud) before anything else touches the port. Never leave the machine in eval serving mode:
  serving_mode.sh daily must run at the end, or OpenCode has no models in the morning.
- Phase 0 step 6, reasoning leak: if <think> lands inside choices[0].message.content instead of a
  separate field, every IFEval constraint and every BCB code extraction is corrupted for thinking
  models. Check it with a real request before building on top of it. eval_proxy.py gets built
  either way (it is what injects neutral sampling for BCB, §3.5 bite 3); the check only decides
  whether it also strips reasoning.
- Phase 3: round-1 fixtures must re-grade BYTE-IDENTICALLY after the grader changes. Prove it.
- Phase 6 gate: aggregate.py must reproduce the EXISTING LEADERBOARD.md composite from the
  existing result files. If it cannot, either methodology.md's formula or the hand-written
  leaderboard is wrong — report that immediately and do not build on top of it.

Phase 4 quality bar (this is where the round can quietly go wrong):
- Every planted bug proven by grade/verify_bugs.py — fails on the buggy file, passes on a fixed
  copy. An unproven key entry turns a correct model into a "miss".
- D3/D4/D5 share ONE identical core document; 60K and 100K only add distractors around it.
- est_ctx_tokens measured with the served tokenizer, not estimated. 30K/60K/100K exist to straddle
  OpenCode's ~74K compaction trigger; a wrong count destroys the point of the series.
- Long-context filler is ASSEMBLED from license-clean real docs via a checked-in manifest with
  sha256s. Do not write 400KB of prose into the repo.

WHEN BLOCKED
Do not invent a workaround silently and do not stall. Record the blocker in
eval/ROUND2_STATUS.md, skip to the next independent item, and keep going. Anything that needs a
human decision goes in a "Needs Denis" section of that file.

DELEGATION
Use subagents for parallel independent work — the phases are mostly independent after Phase 0.
local-llm-engineer for the serving/adapter work, debugger for the reasoning-leak check and the
grader-fixture proofs, data-engineer for aggregate.py / validate_correlation.py. Do not fan out
on trivia; one agent returning a summary beats three returning transcripts.

FINISH BY WRITING eval/ROUND2_STATUS.md:
  - which phases are green, with the gate evidence for each
  - env_health numbers (how many of the 148 Hard tasks have resolvable test imports)
  - the reasoning-leak answer
  - measured wall-clock per BCB config and per IFEval config, extrapolated to 15 configs
  - anything left for Denis to decide
Then commit and push feature/round2-expansion.
```

---

## Before pasting

The reasoning-leak check (Phase 0 step 6) stops llama-swap and loads a model via `unsloth-serve`.
Nothing else may need `:8888` or the GPU while it runs — and the session is instructed to restore
`serving_mode.sh daily` afterwards. If a night ends badly, that is the first thing to check in the
morning: `pgrep -fl llama-swap` should return a process.
