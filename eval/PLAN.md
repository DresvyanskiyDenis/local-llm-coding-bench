# Local-Model Agentic Eval — Master Plan (contract)

**Status:** round 1 COMPLETE — 450 graded units over **15 non-broken configs** / 9 working models (`qwen27` q5 + q4 are `broken: true` and skipped). Round 2 is BUILT on `feature/round2-expansion` and **not yet run**; its live build state is [`ROUND2_STATUS.md`](ROUND2_STATUS.md) · **Owner:** Opus (orchestrator) · **Created:** 2026-07-12
*(Superseded status line, mid-round-1 as of 2026-07-15, kept as record: benchmark RUNNING (resumable) — done: opus/glm/gemma/gpt-oss/northmini; **qwen27 BROKEN** (smoke-failed both quants, skipped); **katdev** partial → resuming @ unit 8; **qwopus** + **ornith** onboarded 2026-07-14/15, queued next.)*

**This file is the 2026-07-12 build contract, and it stays authoritative for the config matrix (§2)** — `harness/CONTRACT.md` §5 specifies `configs.json` as generated from §2 (plus `~/bin/unsloth-serve`), and the machine-readable shipped form of that matrix is `harness/configs.json`. Everything else it used to be the single source of truth for has since moved to a document that owns it:

| Domain | Owner now |
|---|---|
| Config matrix / roster (human-readable) | **this file, §2** — shipped form: `harness/configs.json` |
| Hard interfaces: task / grader / driver / result schemas | [`harness/CONTRACT.md`](harness/CONTRACT.md) |
| How the published run was scored + the honest gaps | [`../docs/methodology.md`](../docs/methodology.md) |
| How to reproduce the run end to end | [`../docs/replication.md`](../docs/replication.md) |
| Round 2 — what gets built, where and how | [`IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md) |

Everything below is the plan as written on 2026-07-12, plus its own in-run updates (§2 and §5 carry notes dated 2026-07-14 / 2026-07-15). Where the shipped harness later contradicted it, the original text is **kept** and annotated in place — this file is a record, not a live spec.

---

## 0. Why this exists

The author is, for now, **constrained to local models** for real work (limited hosted-tool token/quota budget). He needs a **bulletproof, evidence-backed answer** to: *which local model + quant do I actually run day-to-day, and what does each cost me in speed/quality?* — both for his own workflow and to show the team. This is not a toy benchmark; it drives a real decision.

**We test on the real stack Denis uses: Unsloth Studio (serving) + OpenCode (agent client).** Realism over synthetic purity, with a controlled speed-probe layer bolted on for clean numbers.

---

## 1. Hard constraints

- **Machine:** MacBook Pro M4 Max, **36 GB unified**, 14 cores (10P+4E), 32-core GPU. GPU `iogpu.wired_limit_mb=32768`. → weights+KV must fit ~30 GB; realistically **weights ≤ ~24 GB**, leaving ~4 GB for macOS + the OpenCode client (~1.5 GB) + a browser (Denis's literal concern).
- **Serving:** Unsloth Studio (llama.cpp `v9871`) on `127.0.0.1:8888`, **one model at a time**, launched via `~/bin/unsloth-serve <name>`. Gotchas (see `setup/UNSLOTH-CHEATSHEET.md`): silent `:8889` rebind if port busy; **zombie Studio parent** holding `:8888` after child OOM → 502; Studio force-adds `--no-context-shift` → OpenCode freezes (GPU→0%) when a session exceeds real `-c` unless auto-compaction fires first.
- **Client:** OpenCode `1.17.18`. Headless entry: `opencode run [message] --model <id> --agent <name> --auto`. Telemetry: `opencode export <sessionID>` (full transcript + timings JSON), `opencode stats`. Config: `limit.context: 90000` + global `compaction` guard on every local model.
- **Time:** target 16 h; overrun acceptable **because the run is resumable** (Denis will pause and continue next day). Resume is requirement #1.

---

## 2. Roster (10 models + ornith = 11 total) × quant matrix

Q4↔Q5 A/B on **every model that has both quants**. gpt-oss has only native MXFP4 (no axis).

| # | Serve name | Repo | Q5 (on disk) | Q4 (A/B) | Notes |
|---|---|---|---|---|---|
| 1 | `qwen` | unsloth/Qwen3.6-35B-A3B-MTP-GGUF | UD-Q5_K_S ✅ | UD-Q4_K_XL ✅ (`qwen4`) | daily driver, MTP head |
| 2 | `opus` | hesamation/Qwen3.6-…-Opus-Reasoning-Distilled-GGUF | Q5_K_M ✅ | Q4_K_M ✅ (`opus4`) | reasoning/review distill |
| 3 | `glm` | unsloth/GLM-4.7-Flash-GGUF | UD-Q5_K_XL ✅ | **download Q4** | 2nd coding driver, non-MTP |
| 4 | `northmini` | unsloth/North-Mini-Code-1.0-GGUF | UD-Q5_K_XL ✅ | **download Q4** | cohere2moe, OpenCode-trained |
| 5 | `gpt-oss` | ggml-org/gpt-oss-20b-GGUF | MXFP4 ✅ (~12 GB) | — | Harmony format, single quant |
| 6 | `gemma`/`gemma4` | unsloth/gemma-4-26B-A4B-it-GGUF | UD-Q5_K_XL 21.2 GB | UD-Q4_K_XL 17.0 GB | re-add; MoE A4B; **MTP head is a SEPARATE file** (`mtp-…gguf` pre-fetched) — auto-MTP engage = 1st-load check; else non-MTP like glm |
| 7 | `qwen27`/`qwen27q4` | froggeric/Qwen3.6-27B-MTP-GGUF | Q5_K_M 19.5 GB, `-c 65536` | Q4_K_M 16.8 GB, `-c 90112` | **MTP slot.** DENSE 27B (≠ fleet MoE), 77.2% SWE-bench — possible new daily driver. Heavy KV (q8_0 KV + FA on) → **context-capped**. **BROKEN 2026-07-14 — smoke-failed both quants → `broken:true`, skipped.** |
| 8 | `katdev`/`katdeviq4` | bartowski/Kwaipilot_KAT-Dev-GGUF | — | Q4_K_M 19.8 GB `-c 65536` / IQ4_XS 17.7 GB `-c 81920` | **coding slot.** Qwen3-32B agentic-RL SWE finetune (62.4% SWE-bench), **non-thinking** (`--reasoning off`). DENSE → context-capped |
| 9 | `qwopus` | Jackrong/Qwopus3.6-35B-A3B-Coder-MTP-GGUF | Q5_K_M 25.3 GB ✅ (2026-07-15) | — (single quant) | **coding speed-lane.** MoE 35B-A3B, MTP head, **non-thinking** (`--reasoning off` + `enable_thinking:false`), text-only (mmproj ignored). Served at full `-c 131072`, peak ≈27–28 GB |
| 10 | `ornith` | tashfene/Ornith-1.0-35B-MTP-Q4_K_M-GGUF | — (Q4 only) | Q4_K_M ✅ (2026-07-15) | MoE 35B, MTP head, **non-thinking** (RL-trained). Speed-lane companion, no Q5 |
| 11 | *(reserve)* | Seed-OSS-36B (512K ctx, slower) / Nemotron-Cascade-2-30B-A3B (arch-check first) | — | — | optional — add only on Denis's word, each +time |

**Config count ≈ 19** (both quants everywhere except gpt-oss/qwopus/ornith single, KAT-Dev's Q4/IQ4 pair). With qwopus + ornith: 11 models × 2 quants − 1 gpt-oss − 1 qwopus − 1 ornith single = **18**, plus KAT-Dev IQ4 = **19 total**.

> **SUPERSEDED — the ≈19 above is the ex-ante planning figure of 2026-07-12.** It counts 11 model rows including the reserve slot (#11), which was never added, and both quants of `qwen27`, which smoke-failed and was dropped. **Shipped:** `harness/configs.json` holds **17** entries, of which **15** are non-broken (`qwen27` q5 and q4 carry `"broken": true`). Those 15 are the configs the 450-unit round-1 corpus was produced on.

### Serving caveats — ACTUAL, from Stage 0 (local-llm-engineer, 2026-07-12)
Downloads (~170 GB) in progress; serve cases + opencode.json ids added (backups `*.bak-20260712`). Nothing load-verified yet — every "fits ~X GB" is computed. Must-verify before dry-run: (1) all downloads `EXIT=0` (partial `.incomplete` blob = load fail); (2) Gemma-4 first load — does Studio wire the separate MTP head + accept `--reasoning on`; (3) qwen27q4 at `-c 90112` ≈ 29.8 GB — watch `memory_pressure`, drop to 81920 if OOM; (4) qwen27/katdev smoke → well-formed `tool_calls` JSON, not XML leak (the whole point of froggeric's fixed Jinja + bartowski's template); (5) MTP acceptance on **Metal** is disputed (CUDA 2.7× ≠ Metal) — measure it (metric #3), don't assume.

- **Context caps are per-config, NOT 131072.** The two DENSE exotics have ~5× the KV of the MoE fleet. Real server `-c`: qwen27-Q5 = 65536, qwen27-Q4 = 90112, katdev-Q4 = 65536, katdev-IQ4 = 81920 (q8_0 KV + `--flash-attn on`). **Harness must read each config's real `-c`** and: (a) cap the speed probe at `min(80K, real_ctx)` — don't request 80K from a 64K server; (b) note that A/B/C/D tasks are small (<~30K ctx) so caps don't bite them; (c) the compaction-survival metric (#13) only meaningfully applies where `limit.context` > real `-c`.
- **limit.context vs real `-c` mismatch:** all four capped configs are registered at `limit.context: 99000` (raised from 90000 on 2026-07-14), but qwen27-Q5 and katdev-Q4 have a real ceiling ~64K *below* that. They're **direct-served (no `--no-context-shift`)** → they context-shift instead of freezing, and OpenCode compaction (`reserved 9900`) should fire first. Since Q5 and Q4 of each exotic share ONE opencode.json id but have different real `-c`, the harness should pin a safe per-config effective context at run time (our tasks stay well under 64K, so low risk).
- **Nemotron-Cascade-2 (reserve):** llama.cpp arch support + tool-call reliability UNVERIFIED — a 10-min `convert_hf_to_gguf.py` / release-note check gates inclusion.

---

## 3. Axes (Denis's framing)

1. **Quant:** Q4 vs Q5 — *is Q5 worth the ~3–4 GB it costs (browser headroom)?*
2. **Model:** the 9 above.
3. **Task type:** text · coding · review/edit.

Baseline sanity per config: works/broken · **average speed over the whole task** (not first tokens) · Q4↔Q5 delta.

---

## 4. Task suites (real tasks, not toy)

Each task = self-contained dir under `eval/tasks/<suite>/<task-id>/` with: `PROMPT.md` (the agentic instruction fed to `opencode run`), a fixed starting `repo/`, a hidden `grade/` (tests + keys, never shown to the model), and `meta.json` (expected outcome, grading method). Sources: hand-picked HumanEval+/MBPP+/SWE-style problems wrapped as **agentic file-editing tasks**, plus 1–2 realistic multi-file tasks.

- **A. Coding — objective, test-graded.** 3–4 tasks. Model edits `repo/` in OpenCode → run hidden `pytest` → **% tests passing**. No judge.
- **B. Review — semi-objective, planted-bug recall+precision.** 2–3 files with a known planted-bug key. Score **recall** (found/planted) **and precision** (real vs hallucinated). Auto-match to key; Opus adjudicates ambiguous matches from saved output.
- **C. Edit-from-review — objective, test-graded.** Code + review comments (some valid, one deliberate **noise** comment). Model applies fixes → re-run tests → % passing **+ did it correctly ignore the noise**.
- **D. Text — subjective, single-judge (Opus).** (1) summarize a real long tech doc → key-point recall + rubric; (2) brainstorm/design ("3 approaches to X with tradeoffs") → rubric. **One judge (Opus) across all models** to kill judge variance.
- **Speed probe — controlled, raw endpoint (bypasses OpenCode).** Escalating context 2K→8K→24K→48K→80K. Clean prefill/decode/TTFT/MTP curves without agent noise. Run **3× for every config** (cheap → everyone gets speed CIs).

---

## 5. The 13 metrics (all in)

**Speed (decomposed):**
1. **Prefill vs decode, as curves** over {2,8,24,48,80}K — prefill = TTFT driver, the Apple-Silicon bottleneck. Source: server `timings.prompt_per_second` / `predicted_per_second` in the probe.
2. **TTFT per agent turn** — compounds across a 20-turn session. Source: `opencode export` per-request timings / server log.
3. **MTP acceptance rate** (MTP models) — accepted-draft ratio + mean draft length; differs code vs prose. Source: server timings.
4. **Wall-clock to complete a standard task** — prefill+decode+turns combined; the single most decision-relevant number. Source: `opencode run` timestamps.

**Quality & reliability:**
5. **Agentic-loop completion** — finished / stalled / infinite-loop / hit-freeze; turns-to-done; clean termination. Source: `opencode export`.
6. **Stability (quant determinism)** — 3× per task → pass-rate variance. A quant that passes 1/3 is not "keep".
7. **Failure taxonomy** — timeout / OOM / malformed-tool-call / XML-leak / wrong-answer / infinite-loop / refused (not just pass/fail). Tells *why* to drop.
8. **Review precision, not just recall** — planted-bug key; counts hallucinated findings (North Mini's known failure).
9. **Surgical-edit discipline** — touched only what was asked vs "improved" half the file. Source: `git diff` size vs reference.
10. **Quality degradation over context** — finds the bug at 40K as well as at 4K (needle inside a coding task).

**Q4↔Q5 concrete:**
11. **RSS + free RAM under a realistic ~40K context** per quant — literally "does Chrome still fit". Source: `ps`/`footprint`/`memory_pressure` sampled mid-config. **The decisive Q5-worth-it input.**
12. **Think:answer token ratio** — reasoning overhead; a model that thinks 3000 tokens before a one-line edit is expensive in wall-clock even at high tok/s.
13. **Auto-compaction survival** — survives OpenCode's ~75% compaction without the `--no-context-shift` freeze. Go/no-go for long sessions. **2026-07-14: now genuinely testable** — the config rework turned on the `compaction` block (`reserved 9900`, `limit.context 99000` < served `-c 131072` on the MoE fleet, incl. qwopus) and raised `limit.output` 8192 → 32768 so a session grows fast enough to reach the ~74K trigger. **Residual gap:** the current A/B/C/D tasks stay <30K ctx, so none crosses the threshold — recording a #13 result still needs a dedicated long-context task.

---

## 6. Orchestration & resumability (requirement #1)

**Three roles:**
- **Python engine `eval/harness/orchestrate.py`** (runs backgrounded) — the rails. Loops `(model, quant)`; `unsloth-serve` + load-wait + **zombie-check** + serve-verify (`curl /v1/models`); runs probe + smoke + `opencode run` over each task × rep + objective graders; samples RAM; unloads; **atomic checkpoint per unit**; per-task timeouts so a stuck model can't hang the run. Deterministic + idempotent.
  - *(**SUPERSEDED — readiness probe.** The `curl /v1/models` serve-verify above is the 2026-07-12 plan, not what shipped: Studio answers `GET /v1/models` the instant it binds `:8888`, before the weights are loaded, so `harness/orchestrate.py::wait_for_ready` polls a **1-token `POST /v1/chat/completions`** until it returns 200. Original wording kept as the record of the contract as written.)*
- **Sonnet subagent — one per model** — invoked for judgement/mess: interpret ambiguous output, decide `broken`/retry, **assemble sharded GGUFs** ("склеить"), and write the model's Silicon-Bench card + narrative from saved artifacts (keeps Opus context clean). Not needed on the happy path.
- **Opus (me)** — single judge of subjective (text) tasks from saved outputs; final synthesis, leaderboard, Silicon-Bench (`index.html`) update, team report; owns GO / pause decisions.

**Resumability contract:**
- Unit of work = `(model, quant, suite, task, rep)`. Result → one atomic JSON at `eval/results/<model>__<quant>__<suite>__<task>__rep<N>.json`, written only on completion.
- Append-only ledger `eval/results/manifest.jsonl`; engine **skips any unit whose result file exists** → `--resume` is just re-running the engine.
- Pause = kill the process (safe: units are atomic). Continue next day / new session = re-launch with `--resume`. Raw model outputs saved so **grading is re-runnable without re-inferring**.
- **Broken policy** (only exception to 3×): a config that on Stage 1 won't load / calls no tools / emits pure garbage is marked `broken` and skipped for the 3× quality depth (speed probe still attempted). Everything that works gets full 3×.

---

## 7. Schedule (funnel, 3× everywhere it works)

- **Stage 0 — downloads (background, overlapped):** Gemma-4 (Q5+Q4), 2 exotics (Q5+Q4), Q4 for glm & north-mini (~170 GB total, 398 GB free). Stage 1 starts immediately on already-downloaded configs. **Gotcha:** `hf download` 1.11.0 **restarts** (does not resume) an interrupted file after a kill; a subagent's background tasks can be reaped at ~40 min → for the remaining large files run `hf download` from a plain terminal via `nohup` (no session task-lifetime cap). On-disk as of 2026-07-12: glm4, northmini4, gemma(Q5), katdev(Q4) verified; qwen27 Q5/Q4, katdev-IQ4, gemma4 Q4, aux MTP/mmproj still landing.
- **Stage 1 — screening, 1× quality on all ~14 configs:** (*~14 is the ex-ante 2026-07-12 figure; shipped = 15 non-broken of 17 in `harness/configs.json`, see the §2 note*) smoke + **speed probe 3×** + 1× the task suite. ~35–40 min/config. Output: works/broken, rough quality rank, RSS/RAM, first Q4-vs-Q5 read, broken-list.
- **Stage 2 — depth, +2 reps → 3× quality on every non-broken config:** remaining 2 reps of the suite + full 80K probe. Output: variance/CIs, stable pass-rate, final Q4↔Q5 verdict.
- **Stage 3 — synthesis (Opus):** subjective text judging, leaderboard, `index.html` update, `team-report/`, field-log note.
- **Est. ~28–32 h at full 3× everywhere.** Resumable → runs overnight, pause, finish next day.

---

## 8. Fairness / determinism

Same prompts & task dirs across all models; fixed sampling per model family (document temp/top-p/seed per config); **cold vs warm** first-token measured explicitly (prompt-cache reuse); single subjective judge (Opus); all raw outputs + configs saved for audit and re-grading. **Reasoning effort = HIGH for every model** (locked 2026-07-12): we test each model at its strongest, not its fastest — the driver must force high effort (thinking-on) per invocation and the harness records the effort level + think-token count so metric #12 (think:answer ratio) stays honest.

---

## 9. Outputs

- `eval/results/*.json` + `manifest.jsonl` — raw, resumable, auditable.
- `eval/harness/` — orchestrator, probe, graders, opencode-driver, extended smoke.
- Updated `../index.html` (Silicon Bench cards) + `../team-report/`.
- A vault field-log note summarizing the verdict per model+quant.

---

## 10. Open items before launch

1. ~~**Exotic roster (slots 7–8)**~~ — RESOLVED: Qwen3.6-27B-MTP (`froggeric/…`, Q4+Q5) + KAT-Dev-32B (`bartowski/Kwaipilot_KAT-Dev-GGUF`, Q4+IQ4). All 9 models on disk 2026-07-12 (Stage 0 done, 9/9).
2. **Task domain LOCKED (2026-07-12): Python, self-contained + pytest.** A/B/C/D themed on Denis's real work (pandas/polars data-transforms, a FastAPI endpoint, data validation) but each dir self-contained and deterministically pytest-graded — **no live Spark/Databricks cluster**. Plus 1 HumanEval+-style task for public-bench comparability. Build spec: `eval/harness/CONTRACT.md`.
3. **Reasoning effort LOCKED: HIGH for all models** (see §8). Driver forces thinking-on; open sub-item: verify the exact OpenCode/Studio knob for high effort on each local model family (Qwen3.6 thinking toggle vs a `reasoning_effort` param) during driver build.
4. **Dry-run** the whole harness on ONE already-downloaded model (`qwen`) end-to-end to validate before the overnight launch. **Overnight launch = separate explicit GO after a green dry-run.**
4. **Explicit GO from Denis** to start the overnight run.
