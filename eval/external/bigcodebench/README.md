# BigCodeBench-Hard — external lane (Round 2)

148 hard, library-heavy Python tasks, run **single-turn against the raw
`/v1/chat/completions` endpoint** — no OpenCode, no agent, no tools.

> **This lane measures the MODEL. Round 1 measured the HARNESS** (model + agent + tools).
> A divergence between the two is a finding, but only if they were never conflated.
> See `eval/IMPLEMENTATION_PLAN.md` §3.

## ⚠️ The one caveat that must travel with every number

**`pass@1` from this directory is a WITHIN-FLEET number. It is NOT comparable to the public
BigCodeBench leaderboard.**

BigCodeBench's `requirements-eval.txt` pins `numpy==1.21.2`, `numba==0.55.0`, `keras==2.11.0`,
`tensorflow==2.11.0`, `gensim==4.3.2` — none of which have Apple-Silicon wheels. Docker + Rosetta
was rejected on RAM grounds (36 GB unified is already binding with a 35B GGUF resident) and the
official Gradio executor was rejected because it uploads generated solutions to a third-party HF
Space. So: **relaxed pins + `--execution local`**, decided 2026-07-25.

Every config runs under the *identical* executor, so the **ranking is valid** — and the ranking
is what the Spearman correlation in Phase 6 consumes. The **absolute value is not**. The result
JSON says so in its `comparability` field; do not quote it without that sentence.

The honest bound on the whole lane lives in `env_health.json` → `gt_check.gt_pass_rate`: the
fraction of the 148 tasks whose **own canonical solution** passes in this environment. No model
can exceed it.

## Layout

```
bootstrap.sh                  re-runnable venv build (uv only)
requirements-eval-0.2.5.txt   verbatim copy of upstream's pinned list (sha256 in PROVENANCE.md)
install_report.json           what actually installed, and every pin that was relaxed
env_health.py                 import-resolvability + ground-truth executability of the 148 tasks
env_health.json               ^ its output — the number quoted in the writeup
run_bcb.py                    generate -> evaluate -> normalize, per config
smoke_offline.py              full pipeline test with NO model and NO GPU
PROVENANCE.md                 source URLs, sha256s, install date, every deviation from defaults
.venv/  _gen/  _work/         gitignored
```

## Repro, in order

### 1. Build the venv (~10 min, network)

```bash
bash eval/external/bigcodebench/bootstrap.sh          # add --recreate to start clean
```

Installs `bigcodebench==0.2.5` with `--no-deps` (it declares `vllm`, which has no arm64 wheel
and is only imported lazily for `backend == "vllm"`), then a curated runtime set, then
`requirements-eval.txt` with the pins stripped. Ends by asserting that
`bigcodebench.generate` and `bigcodebench.evaluate` both import **without** pulling in `vllm`.

### 2. Measure the environment (no model needed)

```bash
# fast: static import resolvability only
eval/external/bigcodebench/.venv/bin/python eval/external/bigcodebench/env_health.py

# slow (~30-60 min, CPU): also execute all 148 CANONICAL solutions locally
eval/external/bigcodebench/.venv/bin/python eval/external/bigcodebench/env_health.py \
    --gt-check --parallel 4
```

`--gt-check` is the number that matters. Import-resolvability is necessary but not sufficient:
a task can import `numpy` fine and still fail on a relaxed-pin API change. Any task whose ground
truth fails here is an environment error **by construction**, and `run_bcb.py` subtracts exactly
those from the model's denominator when it reports `pass@1_gt_ok`.

### 3. Smoke-test the pipeline (no model, no GPU, ~2 min)

```bash
V=eval/external/bigcodebench/.venv/bin/python
$V eval/external/bigcodebench/smoke_offline.py --mode perfect   # canonical solutions -> should pass
$V eval/external/bigcodebench/smoke_offline.py --mode empty     # prose only -> pass@1 0, n_no_program == N
```

A mock endpoint replies with each task's own canonical solution, `run_bcb.py` is driven against
it with `--no-serve`, and the result is checked. It also verifies — from the *receiving* side —
that `eval_proxy` really forced the neutral sampling block, which is the one thing BigCodeBench's
own client cannot do. Results go to `_work/smoke/`; `eval/results/` is never touched.

### 4. Know the cost before spending a night

```bash
uv run eval/external/bigcodebench/run_bcb.py --estimate
```

Projects wall clock per config from round 1's `probe__*.json` decode rates and TTFTs. As
measured on 2026-07-25: **~13 h of generation for the full 15-config fleet** at 1 rep, ~27 h if
every model runs to the 4096-token cap. `katdev` (17 t/s, ~10 s TTFT) accounts for ~3.5 h of
that on its own. BCB-Hard is therefore **not** a "night 1 alongside IFEval" item at full fleet
scope without deciding that first.

`--estimate` covers **generation only** and is deliberately conservative: it budgets 2000
generated tokens for a reasoning config. Measured against `opus/q4` on 2026-07-26 it predicted
56 min per 148-task config where the real rate gives ~30 min, because that model actually spends
~600 tokens on a Hard task (peak observed 1268 of the 4096 cap). Treat it as an upper bound per
config, and read the evaluation cost below — `--estimate` does not model it at all.

#### Measured cost model (2026-07-26, `opus/q4`, 10-task slice, `--parallel 4`)

**Do not divide `evaluate_s` by the task count.** Two effects make that badly wrong, both
measured by evaluating the same 10 completions four ways:

| run | wall to results |
|---|---|
| 8 completing tasks, `--parallel 4` | 50 s |
| 2 timing-out tasks only, `--parallel 4` | 252 s |
| all 10, `--parallel 4` | 266 s |
| all 10, `--parallel 1` | 580 s |

- **The per-task evaluation timeout is 241 s** (`max(240.0, gt_time) + 1`, `eval/__init__.py:182`)
  — confirmed by the 252 s two-timeout run (241 s + ~11 s startup).
- Of 569 s of serial work, **482 s (85%) is the 2 timeouts** — 20% of the tasks. The 8 tasks
  that complete cost **10.9 s each**.
- Parallel-4 speedup at N=10 is only **2.23× (56% efficiency)**, because the wall is floored by a
  single 241 s timeout and parallelism cannot split one hung task. At N=148 the pool saturates
  and throughput governs instead, so the small slice *overstates* per-task cost.
- `evaluate_s` in the result JSON also carries a **fixed ~120 s grace period** (waiting on the
  upstream `multiprocessing.Manager` leak, see below) that is per *config*, not per task:
  389 s reported = 266 s work + 120 s grace.

Projection for a full 148-task config, by timeout rate (the dominant unknown, and a function of
*model quality* — worse models write more hangs):

| timeout rate | per config | 15 configs |
|---|---|---|
| 0% | 10 min | 2.4 h |
| 10% | 25 min | 6.4 h |
| **20% (observed)** | **41 min** | **10.3 h** |
| 30% | 57 min | 14.2 h |
| 100% (pathological) | 167 min | 41.8 h |

Generation is by contrast **flat**: per-task intervals were 7.6–17.8 s, median 12.0 s,
max/median 1.48, with no truncation at the 4096 cap. ~30 min per 148-task config for `opus/q4`.

**Full sweep, 148 × 15 configs, 1 rep: ~14–27 h** (generation 8–13 h + evaluation 6–14 h),
likely ~18–20 h. **It does not fit one night.**

#### If you need it in one night, cap the slice

At ~29–37 s per task per config all-in (fleet-average generation + evaluation at a 20% timeout
rate), plus ~220 s per config of fixed overhead (model load/unload, grace, startup):

| budget | largest slice, 15 configs |
|---|---|
| 6 h | ~32 tasks |
| **8 h** | **~46–59 tasks — use 48** |
| 10 h | ~60–75 tasks |

> ⚠️ **A slice is not a sample.** `--limit N` is implemented as `--id-range 0-N`, i.e. the
> **first N tasks by index**, not a random draw. Nothing guarantees BigCodeBench's id order is
> uncorrelated with difficulty or library mix, so a 48-task prefix is a biased subset and its
> pass@1 is not an unbiased estimate of the 148-task number. Within-fleet *ranking* survives
> (every config sees the identical subset), which is what the Spearman correlation needs;
> absolute pass@1 does not. Taking a seeded random sample instead would be a code change to
> `run_generate` — not made here.

### 5. Real run

`:8888` must belong to `unsloth-serve`, **not** llama-swap:

```bash
eval/harness/ops/serving_mode.sh eval        # stop llama-swap, hand over the port
uv run eval/external/bigcodebench/run_bcb.py --only opus --limit 10   # dev run
uv run eval/external/bigcodebench/run_bcb.py                          # all non-broken configs
eval/harness/ops/serving_mode.sh daily       # give OpenCode its fleet back
```

`run_bcb.py` aborts loudly if llama-swap holds the port — it will not kill it. `--dry-run`
prints the exact commands and serves nothing.

Per config it: starts the model via `orchestrate.serve_config` (imported, never reimplemented),
starts `eval/harness/eval_proxy.py` on `:8899`, generates through the **proxy** (never `:8888`
directly), unloads the model, evaluates locally, and writes
`eval/results/bcb__<model>__<quant>.json`.

## Memory sandbox: what bounds a runaway task, and what does not

**This machine has 36 GiB, not 128 GB.** Measured, because the number drives every decision
below: `hw.memsize` = 38,654,705,664 (36 GiB), `hw.model` = `Mac16,5` (M4 Max). Any advice
premised on 128 GB does not apply here.

### No memory cap is reachable — reproduced, not inherited

`reliability_guard`'s rlimits are disabled (`--max-as-limit 0 --max-data-limit 0
--max-stack-limit 0`) because they cannot be set at all on this platform. Re-verified
2026-07-26 on macOS 26.5.2 arm64 / CPython 3.12.13:

```
RLIMIT_AS:    soft=9223372036854775807 hard=9223372036854775807 -> ValueError: current limit exceeds maximum limit
RLIMIT_DATA:  soft=9223372036854775807 hard=9223372036854775807 -> ValueError: current limit exceeds maximum limit
RLIMIT_RSS:   soft=9223372036854775807 hard=9223372036854775807 -> ValueError: current limit exceeds maximum limit
```

Setting a 4 GiB **soft** limit below an unlimited **hard** limit is legal under POSIX and still
fails: Darwin does not implement `RLIMIT_AS`. So there is **no per-task memory ceiling**, and
none can be added without a wrapper. That is a permanent property of the platform, not a
configuration mistake.

### What *is* bounded

Each task runs in its own `multiprocessing.Process` with
`timeout = max(240.0, gt_time) + 1` ≥ **241 s**, then `terminate()` → `kill()`
(`eval/__init__.py:182-208`). Confirmed empirically, not just read: evaluating the two hanging
tasks of the gate slice on their own took 252 s wall (241 s + ~11 s startup). So a runaway
allocator can hold memory for at most ~241 s, and the kill reclaims it. Time is bounded and the
process is killable; only the *rate* and *peak* of allocation are not.

**The exposure is therefore 4 × 241 s windows, not an unbounded one** — with `--parallel 4`, at
most four processes can be allocating without a ceiling at any moment, each for at most ~4
minutes. That is what makes "safe as-is on an idle box" defensible; it is also exactly what
stops being true if the box is shared.

> **Do not set `BIGCODEBENCH_TIMEOUT_PER_TASK`.** `max(os.getenv(...), min_time_limit)`
> compares `str` to `float` → `TypeError: '>' not supported between instances of 'float' and
> 'str'` (`eval/__init__.py:182`, `gen/util/__init__.py:105`). Setting it crashes every task.
> The per-task bound must be changed in code, not by env var.

### Recommendation

The dominant risk is **not** `--parallel 4`. It is a resident model during evaluation.

1. **Never evaluate while a model is loaded.** `run_bcb.py` already unloads before evaluating
   (`[unload] RAM released, port clear` precedes `[evaluate]`), which leaves ~30 GB of headroom
   instead of ~10 GB. Two ways to lose that guarantee, both to be avoided at full scale:
   `--no-serve` (leaves the 35B resident through evaluation), and **running the in-harness
   suite concurrently on the same box**. On 36 GB, a 35B GGUF (~20 GB) plus four unbounded
   test processes is the realistic path to a swap storm or a Jetsam kill of something that
   matters. Serialise the two runs; do not overlap them.
2. **`--parallel 4` is acceptable on an idle box, `--parallel 2` if anything shares it.**
   Halving roughly doubles evaluation wall clock (~96 min → ~190 min per 148-task config), so
   pay that cost only when sharing is actually happening.
3. **Prefer a watchdog over lower parallelism** if the wall clock matters: poll the evaluate
   process tree's RSS inside `wait_for_evaluate()` — which already owns the process group and
   already has `kill_group()` — and kill above a budget (~24 GB). ~15 lines, no vendored
   change. It aborts the whole config's evaluation rather than the one bad task, which is why
   it is a fallback and not the default.

**Risk accepted as configured (`--parallel 4`, rlimits off, model unloaded, box otherwise
idle):** up to four concurrent test processes can allocate without limit for up to 241 s each.
A single task allocating >30 GB would push the machine into heavy compression/swap before its
timeout fires. Nothing in the 148-task ground-truth pass or the 10-task gate has exhibited it,
and peak RSS during evaluation is **not currently instrumented** — that is the measurement gap
to close before treating "it has not happened yet" as "it cannot happen".

## Why generation must go through the proxy

BigCodeBench's client accepts only `max_tokens`, `temperature`, `reasoning_effort` and `n`
(`gen/util/openai_request.py:7-14`) and hardcodes `top_p=0.95`. It cannot send `top_k`, `min_p`
or `presence_penalty` — so those fall through to the **per-model server defaults**, which differ
across this fleet (`sampler-coder` carries `--presence-penalty 1.5`, `sampler-qwen` does not).
A repetition penalty of 1.5 on a code benchmark is a real distortion, and an uneven one.
`eval_proxy.py` is the only place it can be neutralised, so it is mandatory, not optional. What
it enforced is copied into every result file under `generation.sampling_injected`.

## Reading the result JSON

```jsonc
{
  "pass@1": 0.0,               // BigCodeBench's own number, over all evaluated tasks
  "pass@1_gt_ok": 0.0,         // same, with environment-broken tasks removed from the denominator
  "n_no_program": 0,           // THE headline health number: empty + unparseable
  "n_empty_completions": 0,    // sanitizer produced an empty string
  "n_unparseable_solutions": 0,// non-empty but `ast.parse` fails => truncated mid-solution, or prose
  "n_empty_raw_completions": 0,// the server itself returned nothing (serving problem, not model)
  "n_sanitizer_dropped": 0,    // sanitizer blanked a non-empty raw response
  "n_env_errors": 0,           // tasks whose own ground truth fails in this environment
  "gt_pass_rate": 1.0,         // ground truth pass rate over THIS RUN'S SLICE only
  "gt_pass_rate_scope": "THIS RUN'S SLICE ONLY (10 task(s)) — ...",
  "untagged_reasoning": { "n_with_prose_before_code_fence": 0, "method": "structural: ...", ... },
  "generation": {
    "sampling_injected": { ... },      // what the proxy forced; see PROVENANCE.md
    "completions_provenance": "this-run — ...",   // or "PARTIAL — ..." / "STALE — ..."
    "reasoning_stripped": { "verdict": "enabled and observed on the TAGGED shapes: ...", ... }
  },
  "executor": { "mode": "local", "pins": "relaxed", "rlimits": "disabled: ...",
                "gt_pass_rate_ceiling": 0.9054,   // ALL 148 tasks — the lane-wide ceiling
                "gt_pass_rate_ceiling_scope": "ALL 148 BigCodeBench-hard tasks ..." },
  "comparability": "within-fleet only; ... NOT comparable to the public BigCodeBench leaderboard",
  "schema_version": 3
}
```

**Check `generation.completions_provenance` first — before the score.** It is the field that
states in words whether the completions being scored were produced by *this* run through
`eval_proxy`. It reads `this-run` (all of them were), `PARTIAL — only N of M ...` (the rest were
reused from disk, under whatever sampling was in force then), or `STALE — 0 requests reached
eval_proxy in this run`. On anything but `this-run`, `sampling_injected` and
`reasoning_stripped` describe a proxy that some of the scored completions never passed through,
and nothing else in the file says so outright — the raw counts it is derived from,
`generation.n_proxy_requests` against `n_completed`, are all you would otherwise have.
`run_bcb.py` defaults to regenerating from
scratch — it moves any earlier samples file aside — so `this-run` is the normal reading; passing
**`run_bcb.py --resume`** is what makes the reused-completions verdicts possible, and it exists
to finish a crashed long run. (That is this script's own `--resume`, not the upstream
`--resume` under "Known upstream behaviours" below, which stays on BigCodeBench's command line
either way.)

The other schema-3 fields, briefly:

- **`generation.reasoning_stripped`** — what the proxy *observed*, not what was asked for. Its
  `verdict` distinguishes "enabled and observed" from stripping that was requested but never
  exercised; `shapes_covered` lists the four tagged wrappers it removes and `shape_not_covered`
  names the one it cannot.
- **`untagged_reasoning`** — measured exposure to exactly that uncovered shape: reasoning prose
  with no delimiter at all. Detection only, structural (text before the first code fence in
  `raw_solution`); no completion is ever modified.
- **`gt_pass_rate` vs `executor.gt_pass_rate_ceiling`** — two different denominators, which is
  why each carries a `..._scope` string. The first is over the tasks *this run* evaluated; the
  second is over all 148, from `env_health.json`, and is the lane-wide ceiling. On a `--limit`
  run they are not interchangeable.

`n_no_program` and `n_env_errors` are **load-bearing**: without them a truncation bug or a
missing `numba` is indistinguishable from a model that genuinely failed the task. All of them are
derived from the artifacts, never assumed.

Emptiness alone is *not* the truncation tell. `sanitize()` returns the response **verbatim** when
it finds no code block, so a model that answered in prose — or stopped mid-function — yields a
non-empty `solution` that is not a Python program. `n_unparseable_solutions` is what catches that,
and `n_no_program = n_empty_completions + n_unparseable_solutions` is the number to look at first.
If it is large, raise `--max-new-tokens` before believing the score.

## Known upstream behaviours worked around

All verified against the *installed* 0.2.5 source; each is a flag, never a patch.

- `generate.py` flushes to disk only at `bs` boundaries or end of split → `--bs 1`, else a
  crashed 148-task run loses everything and `--resume` has nothing to resume.
- `evaluate.py` asserts the samples file covers every problem in the set → `--limit N` is
  implemented as `--id-range 0-N` on generate **plus** `--selective-evaluate <ids>` on evaluate.
- `evaluate.py` calls `input()` when its output files already exist → stale artifacts are moved
  aside and stdin is `/dev/null`, so a scripted run cannot block on a prompt.
- `make_auto_request` retries **forever** on any exception → both subprocesses run under an
  explicit timeout.
- `reliability_guard`'s memory rlimits are unsettable on macOS → `--max-as-limit 0
  --max-data-limit 0 --max-stack-limit 0`. See PROVENANCE.md; without this every task
  env-fails and every model scores 0.
- `make_request` sends the token budget as **`max_completion_tokens`**, not `max_tokens`
  (`gen/util/openai_request.py:16`). Checked, not assumed: the fleet's `llama-server`
  (build 9871, `990fe9b16`) registers `max_completion_tokens` as an alias in
  `tools/server/server-schema.cpp:46`, so `--max-new-tokens 4096` is honoured. If that server is
  ever swapped for one without the alias, generations silently fall back to its default budget
  and `n_sanitizer_dropped` is the tell.
