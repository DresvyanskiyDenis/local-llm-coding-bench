# Round 2 — Implementation Plan

*Created 2026-07-25. Turns [`experiments_expansion_plan.md`](experiments_expansion_plan.md) (what and why)
into a build order for **this** repo (where and how). Companion to
[`harness/CONTRACT.md`](harness/CONTRACT.md), which stays the interface source of truth —
every schema below is an **additive extension** of it, never a rewrite.*

---

## 0. Success criterion

One sentence: **by morning, `uv run orchestrate.py --dry-run` passes with the round-2 tasks
included, and three new commands exist and have each produced a real result file for at least
one config.**

```bash
uv run eval/harness/orchestrate.py --dry-run                    # round-2 tasks discovered, schemas valid
uv run eval/external/ifeval/run_ifeval.py --only opus --limit 20 # → results/ifeval__opus__q4.json
uv run eval/external/bigcodebench/run_bcb.py --only opus --limit 10  # → results/bcb__opus__q4.json
uv run eval/harness/pairwise_judge.py --suite D_text --round 1  # → results/DTEXT_PAIRWISE.json
```

Denis then launches the full 15-config run himself. **This plan does not run the evaluation** —
it builds the thing that runs it. See [§8 Run budget](#8-run-budget-what-the-finished-repo-costs-to-actually-run)
for what that run then costs, because it is larger than round 1 and needs a scoping decision.

---

## 1. Feasibility verdict

**Yes, with one genuine unknown and one hard external constraint.**

Verified live on this machine, 2026-07-25:

| Fact | Status | Consequence |
|---|---|---|
| `bigcodebench==0.2.5` declares `vllm` as a hard dependency | ✅ confirmed from PyPI metadata | Would fail to install on arm64 — **but** `vllm` is imported *lazily* inside `provider/__init__.py::make_model`, only for `backend == "vllm"`. `uv pip install --no-deps` + a curated dep set works. |
| `--execution local` exists | ✅ `evaluate.py:122` — `execution: str = "gradio" # "e2b", "gradio", "local"` | Docker (amd64-only image) is avoidable. |
| `--backend openai --base-url` reaches an arbitrary endpoint | ✅ `provider/openai.py:12` passes `base_url` straight to `openai.OpenAI`; `api_key` falls back to `"none"` | Points at `127.0.0.1:8888/v1` with no patching. |
| `--greedy` and `--resume` are built in | ✅ `generate.py:23,27,159` — greedy forces `n_samples=1, temperature=0` | Matches the 1-rep decision; resumable across crashes for free. |
| `evaluate.py` imports `gradio_client` and `e2b` at module top level | ✅ | Both must be installed even for local execution. Pure Python, no problem. |
| IFEval prompts + official verifier are fetchable without auth | ✅ all 5 files HTTP 200 from `raw.githubusercontent.com/google-research/google-research/master/instruction_following_eval/` (`input_data.jsonl` 207 KB) | No HF token, no `lm-eval` (which drags in `torch>=1.8` as a **core** dep — avoided). |
| `claude` CLI present, `ANTHROPIC_API_KEY` **not** set | ✅ `/opt/homebrew/bin/claude` | The pairwise judge runs through `claude -p`, i.e. against the subscription, not an API key. |
| 414 GB free, `uv 0.11.31` | ✅ | No capacity blocker. |
| **`:8888` is held by `llama-swap`, not `unsloth-serve`** | ⚠️ confirmed live — pid 45518, `-config ~/.config/llama-swap/config.yaml`, backends on `:5800+`, `groups.fleet` with `swap: true, exclusive: true` | **The serving layer changed on 2026-07-21, after round 1 was measured.** See §3.5 — this rewrites the serve lifecycle for both lanes. |
| Sampler flags survived the port | ✅ verified 2026-07-25: `sampler-qwen` = `--temp 0.6 --top-p 0.95 --top-k 20 --min-p 0.0`, identical to `unsloth-serve:68`; `sampler-coder` identical to `unsloth-serve:158` | Sampling is **not** a round-1 → round-2 confound. The port manager changed; the decoding did not. |

### The one genuine unknown

**BigCodeBench's `requirements-eval.txt` will not install as pinned on arm64 / Python 3.12.**
It pins `numpy==1.21.2`, `numba==0.55.0`, `keras==2.11.0`, `gensim==4.3.2` — versions with no
Apple-Silicon wheels. Three ways out; **option 1 is decided (2026-07-25), 2 and 3 are recorded
only so they are not re-proposed**:

1. **Relaxed pins + an honest env-health number** — **DECIDED**. Install the
   same 73 packages unpinned, then run `env_health.py`, which imports every module the 148 Hard
   tasks' tests touch and reports what is missing or version-shifted. Every config is executed
   under the *identical* executor, so the **within-fleet ranking — which is what Spearman needs —
   is unaffected**. The absolute pass@1 is then not comparable to the public leaderboard and
   must be labelled as such wherever it is reported.
2. ~~Docker + Rosetta~~ — **rejected: RAM.** 36 GB unified is already the binding constraint with
   a 35B GGUF resident; a Docker VM plus an emulated amd64 test environment competes for exactly
   the memory the served model needs.
3. ~~Official Gradio remote executor~~ (`--execution gradio`, their default) — **rejected with
   it.** Also not local, and it uploads generated solutions to a third-party HF Space.

`env_health.py` runs in Phase 0 precisely so the size of this problem is known before anything
depends on it.

### The hard external constraint

**Usage limits, not engineering difficulty, are the binding constraint on "do it all tonight."**
On a 5h/7d window, a fully autonomous night of authoring 11 new task directories *plus* two
adapters *plus* the judge will hit the rolling limit before it hits the end of the work. The
phase order in [§9](#9-execution-order-for-the-night) is therefore **strictly by dependency and
by blast radius**: everything that unblocks a *run* lands first, content authoring lands last,
so a limit-stop leaves a repo that is runnable rather than half-wired.

### What is explicitly out of scope tonight

- Running the 15-config evaluation (that is Denis's run, and it is nights, not hours).
- Terminal-Bench / Harbor — deferred in the expansion plan, unchanged.
- IFBench — follow-on, only after IFEval is green.

---

## 2. Ground rules for the build

- Branch `feature/round2-expansion`. Conventional commits, one per phase, each independently
  revertible.
- **`eval/results/*.json` from round 1 is immutable.** Round 2 writes new filenames only
  (`bcb__*`, `ifeval__*`, `DTEXT_PAIRWISE*`, and unit files for new task ids). The 450-unit
  corpus stays byte-identical, or the whole "keep round 1 comparable" premise dies.
- Round-2 code is **additive** to `orchestrate.py`, not a refactor of it. That file survived
  three nights of real runs; the new external runner **imports** from it
  (`from orchestrate import serve_config, unload, wait_for_ready, clear_port`) rather than
  duplicating or restructuring the serve lifecycle. `orchestrate.py` is import-safe — everything
  is behind `if __name__ == "__main__"`.
- `uv` inline-script style (PEP 723 header) for every new script, per `CONTRACT.md`.
- Vendored third-party code goes in `vendor/` directories, **unmodified**, with a
  `PROVENANCE.md` recording source URL, commit/date and `sha256`. Modifying a vendored grader
  would forfeit the entire point of this round.

---

## 3. Two lanes, and why the split matters

**Lane 1 — in-harness (B / C / D expansions).** These run through OpenCode exactly like round 1.
`orchestrate.py::discover_tasks()` walks `tasks/<suite>/*/meta.json`, so **a new task directory
is picked up with zero orchestrator changes**, and `--resume`'s skip-if-done protects the
existing 450 units automatically. This lane measures *the harness* (model + agent + tools).

**Lane 2 — external benchmarks (BigCodeBench Hard, IFEval).** These do **not** go through
OpenCode. They hit `/v1/chat/completions` directly, single-turn, no agent, no tools. They
measure *the model*, not the harness.

### 3.5 Serving — changed since round 1, and it bites in three places

Round 1 was served by `~/bin/unsloth-serve <serve_name>`, one model per invocation, orchestrator
owning `:8888` exclusively. Since **2026-07-21** `:8888` belongs to **llama-swap**, which loads
backends on demand by model id onto `:5800+`, with `groups.fleet: {swap: true, exclusive: true}`
and per-model `ttl`. `unsloth-serve` still exists as the escape hatch and, per its own config
header, is *meant* to fail loud if llama-swap holds the port.

**Bite 1 — `orchestrate.py` will silently kill llama-swap.** `clear_port()` (`orchestrate.py:272`)
SIGTERMs whatever listens on `:8888`, then SIGKILLs every `llama-server` process, on the stated
premise that "we own the port exclusively while this engine runs". That premise is now false. The
intended visible conflict is removed by exactly the function meant to guarantee a clean port.
**Phase 3 must add a guard**: if the `:8888` listener is `llama-swap`, `clear_port()` aborts with
an explicit message instead of killing it. Fail loud, per the same principle the config header
already states.

**Bite 2 — llama-swap cannot express the q4/q5 axis.** One model id → one quant, under the
config's stated "Q4 everywhere" policy. `configs.json`'s 17 entries (15 working) encode q4/q5
pairs via distinct `serve_name`s that only `unsloth-serve` understands. Through llama-swap the
fleet would be ~11 configs, one quant each.

> **Decided 2026-07-25: stop llama-swap for the duration of an eval run and serve with
> `unsloth-serve`, exactly as round 1 did.** This keeps all 15 configs including the q4/q5 axis,
> and keeps round-2 units produced under the same serving stack as the 450 round-1 units — which
> is what the rank correlation depends on. Cost: `:8888` is unavailable for daily OpenCode use
> while a run is in flight, which is already true of any eval night.
>
> Procedure, to be scripted as `eval/harness/ops/serving_mode.sh {eval|daily}`:
> `eval` → stop the llama-swap process, confirm `:8888` free and no `llama-server` alive, then
> hand the port to `orchestrate.py`. `daily` → restart llama-swap and confirm it binds.
> Idempotent, and it records which mode it left the machine in, so a crashed night does not leave
> Denis wondering why OpenCode has no models in the morning.

**Bite 3 — server-side sampler defaults leak into "greedy" runs.** BCB's client hardcodes
`top_p=0.95` and sends `temperature=0` (`gen/util/openai_request.py:17-20`) but sends nothing for
`top_k`, `min_p` or `presence_penalty` — so the per-model server defaults apply, and they differ
across the fleet (`sampler-coder` carries `--presence-penalty 1.5`, `sampler-qwen` does not).
A penalty of 1.5 on a code benchmark is a real distortion, and an uneven one. **Both adapters must
send an explicit neutral sampling block on every request** (`temperature: 0, top_p: 1, top_k: 0,
min_p: 0, presence_penalty: 0, frequency_penalty: 0`) and record it in the result JSON's
`generation` block. Do not rely on the server default being neutral; it is not.

**Consequence for the plan as written:** with the decision above, **both lanes serve through
`unsloth-serve` and both reuse the round-1 lifecycle** — Lane 2 imports `serve_config` / `unload`
/ `wait_for_ready` from `orchestrate.py` as originally planned. The only structural additions are
`serving_mode.sh` (bite 2) and the `clear_port()` guard (bite 1), and the guard now earns its keep
twice over: it is what stops an eval run from silently eating llama-swap when someone forgets to
flip the mode.

---

That distinction must be stated in the writeup. Round 1 measured harness-level performance;
IFEval and BCB-Hard measure model-level performance. When the Spearman correlation is computed,
a divergence may be a harness effect rather than a model effect — and that is a finding, but only
if the two levels were never conflated in the first place.

---

## 4. Phase 0 — prerequisites and de-risking (~45 min, no model needed except step 5)

Nothing downstream is trustworthy until these pass.

1. `mkdir -p eval/external/{ifeval,bigcodebench}`; extend `.gitignore` with
   `eval/external/*/.venv/`, `eval/external/*/_work/`, `eval/external/bigcodebench/_gen/`.
2. **Vendor IFEval** into `eval/external/ifeval/vendor/`: `instructions.py`,
   `instructions_registry.py`, `instructions_util.py`, `evaluation_main.py`, plus the
   Apache-2.0 `LICENSE` and a `PROVENANCE.md` with URLs + sha256 + fetch date. Data →
   `eval/external/ifeval/data/input_data.jsonl` (541 prompts), sha256 recorded.
3. Vendor deps: `absl-py`, `langdetect`, `nltk`, `immutabledict`. Pre-download the `nltk`
   `punkt` tokenizer into a repo-local `NLTK_DATA` so a run never blocks on a network fetch.
4. **BCB venv**: `uv venv eval/external/bigcodebench/.venv`, then
   `uv pip install --no-deps bigcodebench==0.2.5` plus the curated runtime set
   (`openai datasets transformers tqdm termcolor numpy rich appdirs fire multipledispatch pqdm
   tempdir tree_sitter tree-sitter-python wget gradio-client e2b httpx`), then
   `requirements-eval.txt` **with pins stripped**. Then `env_health.py` → record the number of
   Hard tasks whose test imports resolve. **This number goes in the writeup.**
5. **`ops/serving_mode.sh`** (§3.5): `eval` stops llama-swap and hands `:8888` to `unsloth-serve`,
   `daily` restores it. Write and test this **before** step 6, because step 6 is the first thing
   that needs the port.
6. **Reasoning-leak check** *(the one step that needs a quiet machine — run it under
   `serving_mode.sh eval` and flip back to `daily` afterwards)*. Serve one thinking config via
   `unsloth-serve` and send a plain chat request. If `<think>…</think>`
   appears inside `choices[0].message.content` instead of a separate `reasoning_content` field,
   every IFEval format constraint and every BCB code extraction is corrupted for thinking models —
   which would silently invalidate exactly the qwen comparison this round exists to test.
   `opencode_driver.py:194` counts a separate `reasoning` part type, which is *evidence* the
   server already separates it, but that is OpenCode's view, not the raw API's. **Verify, don't
   assume.**
   *Handling:* `eval/harness/eval_proxy.py` — a small pass-through on `:8899` forwarding to
   `:8888`. It is needed **regardless** of the leak answer, because §3.5 bite 3 requires injecting
   neutral sampling for BigCodeBench, which cannot send those parameters itself. Reasoning
   stripping is then just a second thing the same proxy does, switched on by step 5's answer.
7. **Confirm `orchestrate.py --dry-run` still passes** in both serving modes. It reads
   `~/bin/unsloth-serve` for `serve_name` resolution and `~/.config/opencode/opencode.json` for
   model ids — neither has moved, but both are now one layer removed from what actually serves.

**Gate:** phases 1 and 2 do not start until 1–4 are green and 5 has a recorded answer.

---

## 5. Phase 1 — IFEval adapter (~1.5 h)

```
eval/external/ifeval/
├── vendor/            # unmodified google-research code + LICENSE + PROVENANCE.md
├── data/input_data.jsonl
├── run_ifeval.py      # generate + score, per config
└── README.md
```

`run_ifeval.py` — `--only <model>`, `--limit N` (dev), `--out`, `--base-url`:

1. Loop `harness/configs.json` (skipping `broken`), reusing `orchestrate.serve_config` / `unload`
   so serve/ready/zombie-port handling is the proven code path, not a second implementation of it.
   Requires `serving_mode.sh eval` first (§3.5) — assert `:8888` is not llama-swap before the
   first launch, and abort loudly if it is.
2. Per prompt: single-turn `chat/completions`, **no system prompt** (a system prompt would
   contaminate an instruction-following measurement), the explicit neutral sampling block from
   §3.5 bite 3, `max_tokens=1280`, strip reasoning per Phase 0 step 5. Write `response` alongside
   `prompt` — resumable per prompt, same skip-if-done discipline as `orchestrate.py`.
3. Score by importing **`vendor/evaluation_main.py`'s `test_instruction_following_strict` and
   `…_loose`**, not by reimplementing them. Both the constraint functions and the
   strict/loose response-variant logic must stay theirs.

Output → `eval/results/ifeval__<model>__<quant>.json`:

```json
{"benchmark": "ifeval", "model": "opus", "quant": "q4",
 "n_prompts": 541,
 "prompt_level_strict": 0.0, "inst_level_strict": 0.0,
 "prompt_level_loose": 0.0,  "inst_level_loose": 0.0,
 "by_instruction_type": {"length_constraints:number_words": 0.0, "...": 0.0},
 "generation": {"temperature": 0, "max_tokens": 1280, "system_prompt": null,
                "endpoint": "http://127.0.0.1:8888/v1", "reasoning_stripped": true},
 "vendor_sha": "...", "schema_version": 1, "ts": "..."}
```

Headline is `prompt_level_strict`. `by_instruction_type` is not decoration — it is what turns
"qwen is bad at formats" into "qwen fails *these* format classes", which is the actual
corroboration of the malformed-tool-call finding.

**Acceptance:** `--only opus --limit 20` produces a scored file with all four metrics populated
and at least one instruction type at neither 0.0 nor 1.0.

---

## 6. Phase 2 — BigCodeBench Hard adapter (~2.5 h)

```
eval/external/bigcodebench/
├── .venv/            # gitignored
├── bootstrap.sh      # Phase 0 step 4, re-runnable
├── env_health.py     # import-resolvability of the 148 Hard tasks' test deps
├── run_bcb.py        # generate → evaluate → normalize
└── PROVENANCE.md
```

`run_bcb.py` per config (serve lifecycle imported from `orchestrate.py`, `serving_mode.sh eval`
asserted first), pointed **through `eval_proxy.py`**, because
BCB's client offers no way to inject sampling parameters: `make_auto_request` accepts only
`max_tokens`, `temperature`, `reasoning_effort` and `n` (`gen/util/openai_request.py:7-14`), so
`top_k`/`min_p`/`presence_penalty` cannot be neutralised from the CLI. The proxy is the only place
that can, and it is the same component as the Phase-0 reasoning-strip fallback — build it once,
`eval/harness/eval_proxy.py`, listening on `:8899`, forwarding to `:8888`, injecting the neutral
sampling block and stripping reasoning if Phase 0 step 5 says it leaks. It logs every injected
override so the result file can assert what the model actually ran under.

```bash
.venv/bin/python -m bigcodebench.generate \
  --model "<opencode_model_id>" --backend openai \
  --base-url http://127.0.0.1:8899/v1 \        # eval_proxy, NOT :8888 directly
  --split instruct --subset hard --greedy --resume \
  --max-new-tokens 4096          # NOT the 1280 default — thinking models blow that budget
                                 # mid-solution and the sanitizer then sees a truncated program

.venv/bin/python -m bigcodebench.evaluate \
  --split instruct --subset hard --execution local --samples <generated.jsonl>
```

Then normalize their `pass@1` into `eval/results/bcb__<model>__<quant>.json`:

```json
{"benchmark": "bigcodebench-hard", "split": "instruct", "model": "opus", "quant": "q4",
 "pass@1": 0.0, "n_tasks": 148, "n_completed": 148,
 "n_empty_completions": 0, "n_env_errors": 0,
 "executor": {"mode": "local", "pins": "relaxed", "env_health": "…/env_health.json"},
 "bigcodebench_version": "0.2.5", "schema_version": 1, "ts": "..."}
```

`n_empty_completions` and `n_env_errors` are load-bearing: without them a truncation bug or a
missing `numba` is indistinguishable from a model that genuinely failed the task.

**Acceptance:** `--only opus --limit 10` (via `--id-range`) yields a `pass@1` with
`n_env_errors == 0` on those ten, and the wall-clock is recorded so 148 × 15 can be extrapolated
before anyone commits a night to it.

---

## 7. Phase 3–6 — the in-harness work

### Phase 3 — grader changes (~1.5 h)

Both changes are backward-compatible; **round-1 fixtures must re-grade byte-identically**, and
that is a test, not a hope. Fixtures already exist: any `eval/runs/` directory, or the answer
text embedded in the round-1 result JSONs.

**`graders/review_grader.py`** — zero-planted-bug path for the control file:

```python
planted = len(key)                       # 0 for the control
recall    = round(found / planted, 3) if planted else None      # null, NOT 0.0
precision = 1.0 if not findings else 0.0 # control: any finding is a false positive
false_positive_rate = len(findings) / 1  # reported for the control regardless
```

Add `"control": true` to the control task's `grade/key.json`. `digest.py::mean()` already filters
non-numeric values, so a `null` recall drops out of the B mean instead of dragging it to zero —
**verify this rather than assume it**, because a control task silently scored as 0.0 recall would
corrupt every B number in the round.

**`graders/diff_grader.py`** — `noise.json` grows a `kind` field:

```json
{"kind": "out_of_scope | already_done | contradiction | must_survive",
 "file": "src/x.py",
 "required_pattern": "...",
 "conflict_signal": {"answer_must_mention": ["conflict", "contradic", "both comments"]}}
```

`must_survive` is the existing behaviour, made explicit — untagged files keep working unchanged.
`contradiction` is the one case a diff **cannot** grade: the question is whether the model
*surfaced* the conflict, which lives in `answer.txt`, not in the tree. So `diff_grader.py`
gains an `answer.txt` read for that kind only, and reports
`conflict_surfaced: true|false|null`. Note this in the verdict as a *keyword-match* signal —
it is weaker evidence than the diff, and calling it stronger than it is would be exactly the
kind of thing this round is meant to stop doing.

Also spec'd here, tiny and in `orchestrate.py::planned_units()`: **optional per-task `reps` and
`configs` in `meta.json`**. Without it, the round-2 run cost in §8 is not scopeable.

```python
reps = meta.get("reps") or [r for s in stages for r in REPS_BY_STAGE[s]]
```

### Phase 4 — new task directories (~3 h, the quality-critical phase)

Layout is unchanged (`PROMPT.md` + `meta.json` + `repo/` or `source/` + `grade/`), so everything
downstream keeps working. **11 new task directories**, deliberately packing multiple bug classes
per task rather than one task per class — same coverage, less than half the run cost:

| Suite | New tasks | Covers |
|---|---|---|
| `B_review` | `B3_concurrency_ledger`, `B4_io_encoding`, `B5_temporal_money`, `B6_control_nobugs` | 8 classes, ~3 planted bugs each: off-by-one, race, resource leak, swallowed exception, encoding/unicode, float precision, timezone/DST, mutable default arg. **B6 plants nothing** — the false-positive control. |
| `C_edit` | `C3_scope_creep` (out-of-scope), `C4_already_done` (redundant churn), `C5_contradiction` (**2 noise of 5**) | the three new noise kinds + the ratio break |
| `D_text` | `D3_longctx_30k`, `D4_longctx_60k`, `D5_longctx_100k`, `D6_pr_describe` | context degradation + PR description |

Non-negotiables for this phase:

- **Every planted bug must be demonstrated, not asserted.** For each B task, a
  `grade/verify_bugs.py` that fails on the buggy file and passes on a fixed copy. A key entry
  nobody proved is a key entry that turns a correct model into a "miss".
- **C tasks ship a passing ref solution and a failing pre-state**, same as C1/C2.
- **Long-context corpora are assembled, not generated.** `D3/D4/D5` share **one identical core
  document**; 60K and 100K add *distractor* material around that same core, so the key points are
  literally the same at all three sizes and the degradation curve measures degradation rather
  than a content change. Filler comes from license-clean real docs (this repo's own `docs/`,
  llama.cpp and OpenCode documentation — MIT), assembled by
  `tasks/D_text/_build_longctx.py` from a checked-in manifest with sha256s, so the corpus is
  reproducible and no 400 KB of model-written prose enters the repo.
- **`D6_pr_describe`** ships a synthetic multi-file diff (~200 lines) whose fact key is exact by
  construction: changed files, the behaviour change, the breaking change. Graded by key-fact
  recall, reusing B's matching machinery — that is what makes it partially judge-free.
- **Token budgets must be measured, not estimated.** `est_ctx_tokens` in `meta.json` drives
  `orchestrate.py`'s RAM-sampling choice, and 30K/60K/100K exist to straddle OpenCode's ~74K
  compaction trigger. Count with the served tokenizer; a wrong number here quietly destroys the
  point of the whole D3–D5 series.

### Phase 5 — pairwise judge (~2 h, validatable immediately)

`eval/harness/pairwise_judge.py` — needs **no inference**, because round-1 answers are already on
disk. This is the one phase that can be fully finished and fully verified tonight.

- Reads `answer.txt` (or the round-1 result JSON) for every config on a D task, `rep1` only.
- **Judge backend is pluggable via `--judge-cmd`, defaulting to `claude -p`** (no
  `ANTHROPIC_API_KEY` on this machine). Costs subscription usage — see the count below.
- **Position bias**: randomise order per pair with a fixed seed, record which side was shown
  first, and fit an order term. If the order term is significant, the judge is biased and the
  numbers need the swap-and-rejudge treatment; measuring it is cheap, discovering it later is not.
- **Bradley–Terry** via MM iteration in plain numpy — no new heavy dependency.
- Round-robin at 15 configs = **105 pairs/task**. Six D tasks × 105 = 630 judge calls.
  **Recommendation: full round-robin for D1/D2 only** (210 calls — these are the ones that must
  be comparable against the round-1 absolute scores, so they get the exact method), **Swiss
  8 rounds (~60 pairs) for D3–D6** — ~450 calls total instead of 630, with the pairing scheme
  recorded per task.
- Output `eval/results/DTEXT_PAIRWISE.{json,md}`: BT strengths + 95% CI, win matrix,
  order-effect estimate, and — for D1/D2 — **the Spearman correlation between the pairwise
  ranking and the round-1 absolute 0–10 ranking**. That single number tells you whether absolute
  judging was merely low-resolution or actually wrong.

### Phase 6 — aggregation, validation, docs (~1.5 h)

**`eval/harness/aggregate.py` — new, and the one addition this plan makes beyond the expansion
plan.** `LEADERBOARD.md` was written by an agent session, not generated by code. For a round
whose entire thesis is "graders nobody here wrote", the ranking itself must be reproducible from
the result files. It encodes:

- explicit `ROUND1_TASKS` / `ROUND2_TASKS` sets, so **the round-1 composite stays exactly
  reproducible** as new tasks land;
- the composite formula, verbatim from `methodology.md`:
  `0.35·A + 0.25·(1 − tool_malformed%) + 0.15·C + 0.10·B_recall + 0.10·(D/10) + 0.05·(decode/137)`;
- new axes (`bcb_hard_pass@1`, `ifeval_prompt_strict`) reported **alongside, unweighted** — the
  expansion plan is explicit that re-weighting waits for evidence of correlation.

**`eval/harness/validate_correlation.py`**: Spearman ρ with p-value and n between the round-1
composite and each external ranking, per axis and on the composite, over the configs both cover.
Small script, and it is the deliverable of the round.

Docs, same commit as the code: `docs/methodology.md` (§ round 2: what changed, the relaxed-pin
caveat, model-level vs harness-level), `harness/CONTRACT.md` (the additive schema fields),
`bench/README.md` and root `README.md`, and `eval/external/*/README.md` with exact repro commands.

---

## 8. Run budget — what the finished repo costs to actually run

The build is one night. **The run is not**, and this is the number worth reading before launching
anything:

| Lane | Units | Notes |
|---|---|---|
| BCB Hard | 148 tasks × 15 configs × 1 rep | generation is the cost; local execution is minutes |
| IFEval | 541 prompts × 15 configs × 1 rep | ~30 min/config at fleet speeds → one night total |
| B_review +4 tasks | 4 × 15 × 3 = **180 units** | ~4 min/unit ≈ 12 h |
| C_edit +3 tasks | 3 × 15 × 3 = **135 units** | ≈ 9 h |
| D_text +4 tasks | 4 × 15 × 3 = **180 units** | **not** ~4 min/unit — see below |
| **Total new in-harness** | **495 units** | more than round 1's 450 |

**The 100K-context tier dominates.** A 100K-token prefill plus generation is minutes per unit, not
seconds; `D5` alone at 15 × 3 is plausibly 6–10 h. Two levers, both already built in Phase 3's
per-task `reps`/`configs` override:

- **Recommended:** `D4`/`D5` at **1 rep** (the degradation curve is a within-model comparison —
  three reps of a slow tier buy little), and optionally restrict `D5` to one quant per model
  (9 configs instead of 15).
- Stage the nights: **night 1** = IFEval + BCB (both 1 rep, both external, both unblock the
  Spearman result); **night 2** = B + C; **night 3** = D.

That ordering matters: night 1 alone produces the round's headline claim. If nights 2–3 never
happen, the answer to the teamlead still exists.

---

## 9. Execution order for the night

Dependency-ordered, and ordered so a usage-limit stop leaves something runnable:

| # | Phase | Gate before proceeding |
|---|---|---|
| 1 | Phase 0 — vendor, venvs, `env_health` | vendored sha256s recorded; `env_health.json` written; reasoning-leak answer recorded |
| 2 | Phase 1 — IFEval | `--limit 20` scores one config, four metrics populated |
| 3 | Phase 2 — BCB | `--limit 10` gives `pass@1` with `n_env_errors == 0`; wall-clock recorded |
| 4 | Phase 3 — graders | round-1 fixtures re-grade **byte-identically**; control path returns `recall: null` |
| 5 | Phase 5 — pairwise judge | runs end-to-end on round-1 D answers; order effect estimated |
| 6 | Phase 6 — `aggregate.py` | reproduces the **existing** `LEADERBOARD.md` composite from result files |
| 7 | Phase 4 — new tasks | each B bug proven by `verify_bugs.py`; each C ref solution passes; D token counts measured |
| 8 | — | `orchestrate.py --dry-run` all-PASS; commit; push `feature/round2-expansion` |

Phase 4 is last **on purpose**, despite being the most visible work: everything above it is
verifiable without a model and without judgement calls, whereas 11 hand-authored task directories
are exactly the kind of thing that should not be rushed against a usage limit at 4 a.m. If the
night ends early, it ends with the external lane working — which is the lane that answers the
authorship objection.

Phase 6's gate is the sharpest test in the list: if `aggregate.py` cannot reproduce the current
leaderboard from the current result files, then either the formula in `methodology.md` or the
hand-written leaderboard is wrong, and **that needs to be known before round 2 builds on top of
it.**

---

## 10. Decisions parked for Denis

Not blockers — the plan proceeds under the stated default in each case — but each changes the
result, so each gets flagged rather than silently chosen:

1. ~~**BCB executor**~~ — **decided 2026-07-25: relaxed-pin local execution.** Docker/Rosetta
   rejected on RAM grounds (36 GB unified is already the binding constraint while a 35B GGUF is
   resident); the Gradio remote executor is rejected with it. Consequence, to be carried into the
   writeup: BCB-Hard `pass@1` is a **within-fleet** number, not comparable to the public
   leaderboard — every config runs under the identical executor, so the ranking (what Spearman
   needs) holds, the absolute value does not.
2. **D5 scope** — default is 1 rep × 15 configs. Full 3 reps adds roughly a night on its own.
3. **Judge usage** — ~450 `claude -p` calls against the subscription, not an API key. If that
   window is needed elsewhere, `--judge-cmd` takes an API-backed alternative unchanged.
4. **Re-weighting the composite** — deliberately *not* done. BCB and IFEval land as unweighted
   reported axes until the correlation is known, per the expansion plan.
5. ~~**Serving stack**~~ — **decided 2026-07-25: llama-swap is stopped for the run and
   `unsloth-serve` serves, as in round 1.** Keeps all 15 configs including the q4/q5 axis, and
   keeps the serving stack constant across rounds. `:8888` is then unavailable for daily OpenCode
   use while a run is in flight. Mechanised as `ops/serving_mode.sh {eval|daily}` (§3.5).
