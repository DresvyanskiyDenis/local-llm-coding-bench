# REPLICATION — reproduce this benchmark from scratch

This is the step-by-step guide to re-run the local-LLM coding benchmark end to end: stand up a
local OpenAI-compatible server, smoke-test it, run the full resumable eval, aggregate the scores,
and compare against the published leaderboard.

Authoritative design docs, read alongside this guide:
- [`eval/PLAN.md`](https://github.com/DresvyanskiyDenis/local-llm-coding-bench/blob/main/eval/PLAN.md) — the master contract (why, config matrix, 13 metrics, resumability).
- [`eval/harness/CONTRACT.md`](https://github.com/DresvyanskiyDenis/local-llm-coding-bench/blob/main/eval/harness/CONTRACT.md) — the hard interfaces (task/grader/driver/result schemas).
- [`METHODOLOGY.md`](methodology.md) — the scoring method + honest gaps.
- [`LEADERBOARD.md`](leaderboard.md) — the published numbers you are reproducing.

Everything runs as PEP-723 inline-script style: `uv run <script>`. There is **no project venv** —
`uv` resolves each script's declared deps on the fly. Never use `pip`.

---

## 1. Hardware / OS prerequisites

| Requirement | Value used for the published run |
|---|---|
| Machine | Apple Silicon Mac (M1–M4). Reference: **MacBook Pro M4 Max** |
| Unified memory | **36 GB** (≥32 GB required — one model at a time must fit in ~24 GB of weights + KV) |
| OS | macOS (the harness shells out to `lsof`, `pgrep`, `vm_stat`, `ps`, `caffeinate`, `memory_pressure`) |
| Python | **≥ 3.11** (declared in every script's `# requires-python` header) |
| `uv` | required — runs every harness/bench/grader script. `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| Disk | ~170 GB free if downloading the full fleet of GGUFs; far less for a single model |
| `opencode` CLI | required to run the eval (the driver shells out to `opencode run` / `opencode export`) |

RAM budget rationale (PLAN §1): weights must fit ~24 GB, leaving ~4 GB for macOS + the OpenCode
client (~1.5 GB) + a browser. That is why only **one model is served at a time**.

> Note on the GPU wired limit: the serving stack raises `iogpu.wired_limit_mb` to `(RAM − 4 GB)`.
> The team installer does this as an opt-in `--with-system` step (a sudo LaunchAgent). Without it,
> the larger 24–28 GB models may not fully offload to the GPU.

---

## 2. Stand up a local OpenAI-compatible server

The benchmark drives whatever answers on **`http://127.0.0.1:8888/v1`** in OpenAI-compatible form.
Two paths:

### Path A (recommended) — the exact stack under test: Unsloth Studio + `unsloth-serve`

The `setup/` folder ships the full team installer (Unsloth Studio = patched `llama.cpp`, the
`~/bin/unsloth-serve` launcher, an OpenCode config, and the shell env with the API key).

```bash
cd setup/team-setup       # (or wherever setup/ places install.sh — see setup/README.md)
./install.sh              # interactive; answer y to each step
```

During install:
1. Log in to HuggingFace with a free token when prompted (this is what makes downloads work,
   even behind a corporate VPN).
2. Pick model(s) to download at the models prompt. To reproduce the #1 result start with
   `ornith` (~22 GB); you do **not** need all eight to begin.

Then, in a **new terminal** (so `~/.zshenv` loads the `PATH` + `UNSLOTH_STUDIO_API_KEY`):

```bash
unsloth-serve ornith      # serves the picked model on 127.0.0.1:8888; wait for "model loaded"
```

`unsloth-serve` accepts one of the 8 public fleet names:
`ornith | gemma | qwopus | opus | glm | northmini | qwen | gpt-oss` (default `qwen`). Serve exactly
one at a time — 36 GB holds one; stop it (Ctrl-C) before starting another.

> **Full-matrix caveat.** The published run tested most models at **both q4 and q5** (see
> `eval/harness/configs.json`, which references serve names like `qwen4`, `opus4`, `glm4`,
> `northmini4`, `gemma4`, plus the `katdev`/`qwen27` exotics). The *public* `unsloth-serve` ships
> one quant per model and 8 models only. To reproduce the entire q4↔q5 matrix you must add a
> `unsloth-serve` case for each quant variant (pointing at that quant's GGUF) whose label matches
> the `serve_name` in `configs.json`. To reproduce a **single model at its published quant**, the
> 8-model launcher is enough — trim `configs.json` to just that config (see §4).

### Path B — any other localhost:8888 OpenAI-compatible endpoint

Nothing in the harness is Unsloth-specific at the protocol level: it POSTs
`/v1/chat/completions` with `tools` and reads `choices[].message.tool_calls` + `timings`. Any
server that speaks that on `127.0.0.1:8888` (plain `llama-server`, LM Studio, etc.) works. If it
listens elsewhere, the smoke test takes `--base-url`, but `orchestrate.py`/`speed_probe.py`/the
driver hardcode `127.0.0.1:8888`, so serve there for a faithful run. Also register each model id in
`~/.config/opencode/opencode.json` under `provider.unsloth-studio.models` (the driver and the
dry-run check both read it) — the models declaring `"reasoning": true` are the ones the driver runs
at high effort (`opencode run --variant high`).

**API key:** every client reads `UNSLOTH_STUDIO_API_KEY`, falling back to the literal dev key
`sk-local-dummy-key`. Path A sets it in `~/.zshenv`. For Path B, either export it or pass
`--api-key` to the smoke test (the other scripts only read the env var).

---

## 3. Smoke test — confirm the endpoint answers and drives tools

Once a model is serving, verify tool-calling before spending hours on the full eval:

```bash
# human-readable table
uv run bench/smoke_test.py --model <opencode-model-id>

# machine-readable (what orchestrate.py runs internally)
uv run bench/smoke_test.py --model <opencode-model-id> --json

# repeat the 6-scenario suite N times
uv run bench/smoke_test.py --model <opencode-model-id> --rounds 3
```

Concrete example for the `ornith` model:

```bash
uv run bench/smoke_test.py --model tashfene/Ornith-1.0-35B-MTP-Q4_K_M-GGUF --json
```

Flags (verified against `bench/smoke_test.py`): `--base-url` (default
`http://127.0.0.1:8888/v1`), `--model` (default `unsloth/Qwen3.6-35B-A3B-MTP-GGUF`), `--api-key`
(default: `$UNSLOTH_STUDIO_API_KEY` → `sk-local-dummy-key`), `--json`, `--rounds N`.

The suite runs 6 scenarios (single call, nested-object args, multi-turn chain, parallel calls, a
no-tool control, long-context call). Read `overall tools:` — `pass` / `partial` / `fail`. A `fail`
here is exactly what `orchestrate.py` uses to mark a config `broken` and skip its quality depth, so
a green smoke is the gate for a real run.

---

## 4. Run the full eval

### 4a. Dry-run first (no model launched)

`orchestrate.py` validates the whole harness offline: `configs.json` schema, every `serve_name`
resolves to a case in `~/bin/unsloth-serve`, every `opencode_model_id` is registered in
`~/.config/opencode/opencode.json`, every task dir parses, and the graders/driver compile.

```bash
cd eval/harness
uv run orchestrate.py --dry-run     # must show 0 FAIL before any real launch
```

### 4b. What `configs.json` controls

`eval/harness/configs.json` is the outer loop — one object per `(model, quant)`. Each entry:

```json
{
  "model": "qwen", "quant": "q5",
  "serve_name": "qwen",                              // arg passed to ~/bin/unsloth-serve
  "opencode_model_id": "unsloth/Qwen3.6-35B-A3B-MTP-GGUF",
  "real_ctx": 131072, "probe_max_ctx": 80000,
  "mtp": true, "reasoning": "on", "broken": false
}
```

- Add/remove configs to change the roster. `"broken": true` skips a config entirely (that is how
  `qwen27` is excluded — it smoke-failed both quants).
- `serve_name` must match a `unsloth-serve` case; `opencode_model_id` must be registered in
  `opencode.json`. The dry-run enforces both.
- **To reproduce just one model**, trim `configs.json` to that entry (or use `--only <model>`,
  which filters by the `model` field — note it selects *all* quants of that model).

### 4c. Reps and stages

`orchestrate.py` runs 3 reps per task, split into stages (`REPS_BY_STAGE`):
- **Stage 1** = rep 1 only (screening: smoke + 3× speed probe + 1× the task suite).
- **Stage 2** = reps 2 and 3 (depth → variance/CIs, stable pass-rate).
- Omitting `--stage` runs stage 1 then stage 2 (the full 3×).

Suites and tasks are auto-discovered from `eval/tasks/{A_coding,B_review,C_edit,D_text}/*/meta.json`.
The published set is **10 tasks** (A×4, B×2, C×2, D×2) → 10 tasks × 3 reps = **30 units per
model×quant**.

### 4d. The run commands

Direct (foreground; simplest, one config at a time is fine because it's resumable):

```bash
cd eval/harness

uv run orchestrate.py --resume --stage 1                 # stage 1 across all configs
uv run orchestrate.py --resume --stage 2                 # then depth
uv run orchestrate.py --resume                           # or: both stages in one go
uv run orchestrate.py --resume --only ornith             # restrict to one model (all its quants)
uv run orchestrate.py --resume --stage 2 --only qwen     # one model, one stage
uv run orchestrate.py --resume --agent build             # opencode --agent name (default: build)
```

`--resume` is **mandatory** to launch models (the script refuses without it — `--dry-run` is the
validate-only mode). Resumability is a hard guarantee: a unit is "done" iff
`eval/results/<unit>.json` exists, so re-running the same command just skips completed units and
picks up where it stopped. Kill the process anytime (Ctrl-C / SIGTERM) — you lose at most the
in-flight unit; per-task `timeout_s` (900 s in the tasks) stops a hung model from stalling the run.

Per config, the engine: clears `:8888` → `unsloth-serve <serve_name>` → waits for a real 200 from
`/v1/chat/completions` (zombie/rebind-checked) → 3× speed probe → smoke → each `(suite, task, rep)`
via `opencode_driver.py` + the matching grader(s) → samples RAM once (during the largest-context
unit) → writes the atomic unit JSON → unloads the model before the next config.

### 4e. Detached / unattended runs (recommended for the overnight matrix)

The agent that built this had its tracked background tasks reaped, so the ops layer runs each model
in its **own detached session** with a `caffeinate` wrapper + a janitor watchdog, and reconciles
from on-disk markers:

```bash
cd eval/harness
uv run ops/spawn.py ornith          # detaches run_model.sh ornith → own session; returns immediately
# run_model.sh: caffeinate + watchdog + `orchestrate.py --resume --only <model>` + 6h wall-cap,
# then writes eval/results/DONE__<model>.marker
```

`ops/run_queue.sh` chains every remaining model strictly serially (one in RAM at a time), digesting
each as it finishes and skipping any that fails — the self-driving path for the whole fleet.

### 4f. Where results land

Everything under `eval/results/` (the only tracked eval output; `eval/runs/` is regenerable scratch
and git-ignored):

- `eval/results/<model>__<quant>__<suite>__<task>__rep<N>.json` — one atomic file per completed
  unit (schema in CONTRACT §4: `driver` metrics + `grade` verdict + `ram` sample + `served` info).
- `eval/results/manifest.jsonl` — append-only ledger, one line per unit `{unit_id, status,
  pass_rate, ts}`.
- `eval/results/probe__<model>__<quant>.json` — speed-probe curves.
- `eval/results/smoke__<model>__<quant>.json` — smoke verdict.
- `eval/results/logs/` — serve/orchestrate logs (git-ignored; may contain the endpoint key).

### 4g. Roughly how long

PLAN §7: ~35–40 min per config for stage 1; **~28–32 h at the full 3× across the whole ~17-config
matrix**. It is designed to run overnight, pause, and finish the next day — resume is requirement
#1. A single model×quant at full 3× is roughly 1.5–2 h. The published leaderboard is **450 graded
units across 9 working models**.

---

## 5. Aggregate & score

### 5a. Per-model deterministic digest

After a model's units exist on disk, roll them up with `digest.py` (side-effect-free, this is what
the detached queue runs after each model):

```bash
cd eval/harness
uv run digest.py ornith        # reads results/ornith__*.json + probe__ornith__*.json
# → writes eval/results/DIGEST__ornith.md and prints it
```

Per quant it reports: A_coding pass-rate, C_edit pass-rate + surgical-score + noise-acted count,
B_review recall/precision + hallucination total, D_text unit count (qualitative — judged
separately), speed-probe decode/prefill t/s, tool-call malformed rate, termination breakdown, and
peak RAM. Run it for each model to regenerate all `DIGEST__*.md`.

### 5b. D_text (offline judge)

D_text units are saved by the driver but **not auto-graded** (`grader: "judge"`, `grade: null` in
the unit JSON). They are scored 0–10 by a single offline LLM judge (Opus, to kill judge variance),
and the results are consolidated into `eval/results/DTEXT_JUDGED.json` / `.md`. This is the one
metric that requires a judging pass rather than a deterministic script.

### 5c. Cross-model rollup + composite (the LEADERBOARD numbers)

The metrics `digest.py` doesn't cover (TTFT cold/warm, wall-clock, turns, think:answer ratio, etc.)
are aggregated into `eval/results/METRICS_ROLLUP.md` + `eval/results/metrics_rollup.json`, and the
per-suite `q4/q5` table into `eval/results/LEADERBOARD.md`. The headline composite is one explicit,
auditable weighting (from METHODOLOGY.md / LEADERBOARD.md), applied to each model's **q4** (or
single) quant with decode normalized to the fleet max of 137 t/s:

```
Overall = 0.35·A_coding + 0.25·(1 − tool_malformed%) + 0.15·C_edit
        + 0.10·B_recall + 0.10·(D_text/10) + 0.05·(decode/137)      → ×100
```

To regenerate the LEADERBOARD-equivalent numbers: run `digest.py` for every model (5a), judge the
D_text units (5b), then apply the formula above to the per-model digest values (A pass-rate,
1−tool-malformed%, C pass-rate, B recall, D judge mean, decode t/s). The composite and the
`METRICS_ROLLUP` / `eval/results/LEADERBOARD.md` tables were assembled in the Stage-3 synthesis from
those digest + rollup inputs, not by a single committed scoring binary — the formula is the
reproducible spec, and every input is a deterministic digest field, so the numbers are auditable and
re-derivable from `eval/results/`.

### 5d. Reading a mid-run table — `‡`, `⚠`, and what the fraction does not count

`aggregate.py` recomputes the composite from the result files alone and renders a markdown table
next to the JSON:

```bash
uv run eval/harness/aggregate.py --round all --out eval/results/AGGREGATE__roundall.md
```

The JSON lands at `eval/results/AGGREGATE__roundall.json` — the `__round<N>` suffix means
`--round 2` / `--round all` never overwrite the committed round-1 `AGGREGATE.json`. `--out` has no
such protection: it overwrites exactly the path you name, so name it to match the round you asked
for. Pointing a `--round all` run at `AGGREGATE.md` replaces the published round-1 table with a
31-task one, silently. Run this before the matrix has finished and you will hit two
markers. Both are deliberate; the argument for them is `docs/methodology.md` §6.12, this is how to
read them.

**`‡` means "measured over less than the whole thing" — but *which* whole thing depends on the
column.** In the `cov` column it is tasks: `cov` is how many tasks of the selected task set this
config has units for, rendered as a fraction with a trailing `‡` when it is short — both composites
on that row were then computed from exactly those tasks and no others, out of the 31 that
`--round all` defines. In the **BCB-Hard** and **IFEval** columns the same marker counts
items of the *benchmark's* full set instead: `0.300 ‡10/148` is a BigCodeBench pass@1 over 10 of the
148 hard tasks, and `0.250 ‡20/541` is an IFEval score over 20 of 541 prompts (both are the real
cells in the committed `eval/results/AGGREGATE.md`, from a gate probe). Same symbol, two
denominators — do not read a `‡` in the external columns as a statement about your task coverage,
and never compare two `‡` numbers to each other unless the fractions match: two differently-sized
slices of the same benchmark are not the same measurement.

**`⚠` is strictly stronger than `‡`, and it is the one you must not average away.** `‡` says small
sample; `⚠` says the sample it *does* cover is contaminated. It is raised on an IFEval cell when
`n_finish_length > 0` — responses that hit the token ceiling without finishing and were scored
anyway. In the committed table `opus__q4` reads `0.250 ‡20/541 ⚠` because 15 of its 20 scored
prompts truncated (`eval/results/ifeval__opus__q4.json`, `n_finish_length: 15`), and for a config
whose reasoning arrives without a `<think>` tag the stripper cannot fire, so that monologue was
graded as the answer. A `‡` number gets better when you run more items. A `⚠` number does not — more
items of the same shape just produce more contaminated ones. The harness only detects this; nothing
is re-scored, and the underlying leak is an open decision (`eval/ROUND2_STATUS.md`, "Needs Denis"
#0).

**The trap: `cov` counts tasks, not reps.** A task counts as covered the moment **one** unit file
for it parsed. Reps are not part of the fraction. So a config that has finished exactly one of the
three reps on every task reads `cov 31/31` with no `‡` at all — a complete-looking row whose every
axis is a mean over a third of the intended samples, and §6 below is explicit that a single pass is
noise. This is the failure mode most likely to bite you mid-run, because the marker you are trained
to look for is *absent*. `cov` answers "did this task produce anything?", never "did it produce
enough?". Cross-check rep depth separately — count the `__rep<N>.json` files per task under
`eval/results/` — before treating an unmarked row as settled. The same caveat applies in the other
direction: a row can be `‡` on `cov` and still have full 3-rep depth on the tasks it does cover.

**Script against the JSON, not the markdown.** Every marker has a machine-readable original, so
there is no reason to parse a table. Each config row carries `coverage` with `tasks_with_units`,
`tasks_in_set`, `fraction`, a `complete` boolean, a `complete`/`PARTIAL` `status`, the
`missing_tasks` ids and a `by_suite` breakdown, plus a one-line `composite_coverage` sentence
sitting next to the composite it qualifies. The external lane lives under
`external_axes_unweighted[<axis>][<model>__<quant>]` with `n_measured`, `n_full_set`,
`denominator_unit`, `measured_field`, `full_set_source`, `status`, the artifact's `ts` and
`source_file`, and — for IFEval — `truncation_contamination`. Gate `coverage.complete` and
`status == "complete"` in your own tooling; the markdown is for humans.

**`UNKNOWN` is not a variant of `complete`.** If an artifact carries no count field for what it
scored, the status is `UNKNOWN` and the cell renders `‡?/148` rather than being assumed to be a full
run. `full_set_source` tells you where the denominator itself came from, which is not always the
artifact: BigCodeBench's writes no available-count field at all, so 148 is a fallback constant, and
an IFEval artifact written before `n_prompts_available` existed (`schema_version: 1` — the committed
`ifeval__opus__q4.json` is one) falls back to 541 and says so. Treat `UNKNOWN` as *not* a full-set
score until it is re-run with a denominator on record.

**What to do about it: read partial rows, do not quote them.** A partial number is genuinely useful
while the matrix is running — it tells you the pipeline is producing sane values and lets you catch a
broken config early. It is not a result. Do not put a `‡` or `⚠` row in a comparison table, a
README, or an issue comment without its fraction attached, and do not compare it against the
published leaderboard (§6): those numbers are complete-coverage, round-1-weighted, full-3-rep
figures. Wait for `cov n/n` with no marker, confirm rep depth, and only then compare.

---

## 6. Compare to the published results

The published answer is [`LEADERBOARD.md`](leaderboard.md) (top-level narrative) backed by the
computed [`eval/results/LEADERBOARD.md`](https://github.com/DresvyanskiyDenis/local-llm-coding-bench/blob/main/eval/results/LEADERBOARD.md) and
[`eval/results/METRICS_ROLLUP.md`](https://github.com/DresvyanskiyDenis/local-llm-coding-bench/blob/main/eval/results/METRICS_ROLLUP.md). Compare your regenerated
`DIGEST__*.md` + composite against those tables.

**Non-determinism caveat.** Local LLM inference on Metal is **not bit-reproducible** — sampling,
llama.cpp/Studio version, MTP acceptance, quant build, and background system load all move the
numbers. Expect your figures to land in the **same magnitude and ordering, not identical values**.
That is exactly why the design runs **3 reps per task** (metric #6, stability/variance): a single
pass is noise, and a quant that passes 1/3 is not "keep". Judge a reproduction by whether the
per-dimension winners and the broad composite tiers reproduce, not by matching a score to the
decimal. Known measurement gaps (MTP acceptance rate, the 80 K probe point, long-context decay,
auto-compaction survival) are documented honestly in METHODOLOGY.md and will be null/absent in your
run too unless you extend the task set.
