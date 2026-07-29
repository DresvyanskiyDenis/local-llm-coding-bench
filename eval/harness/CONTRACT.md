# Build contract — eval harness interfaces (source of truth for parallel build)

Everything below is a **hard interface**. Three components are built in parallel by
separate agents; they only fit together if every path, CLI signature, and JSON schema
here is honored **exactly**. If something is underspecified, pick the simplest option
that satisfies the schema and note it in your return — do NOT invent new fields.

Read `../PLAN.md` first (the why + the config matrix §2). This file is the *how*.

Domain (locked): **Python, self-contained, pytest-graded.** No live Spark/Databricks.
Reasoning effort (locked): **HIGH for every model under test.**

---

## 0. Directory layout (create exactly this)

```
eval/
├── PLAN.md                      # contract (done)
├── harness/
│   ├── CONTRACT.md              # this file
│   ├── speed_probe.py           # DONE — do not touch
│   ├── opencode_driver.py       # COMPONENT 2
│   ├── graders/
│   │   ├── pytest_grader.py     # COMPONENT 2
│   │   ├── review_grader.py     # COMPONENT 2
│   │   └── diff_grader.py       # COMPONENT 2
│   ├── configs.json             # COMPONENT 3 generates (schema §5)
│   └── orchestrate.py           # COMPONENT 3
├── tasks/                       # COMPONENT 1
│   ├── A_coding/<task-id>/
│   ├── B_review/<task-id>/
│   ├── C_edit/<task-id>/
│   └── D_text/<task-id>/
├── runs/                        # ephemeral per-unit working copies (git-ignored)
└── results/
    ├── <unit>.json              # one atomic file per completed unit
    └── manifest.jsonl           # append-only ledger
```

All harness scripts are **uv inline-script style** (PEP 723 header like `speed_probe.py`),
run via `uv run <script>`. Python ≥3.11. No project-level venv.

`<unit>` filename = `<model>__<quant>__<suite>__<task>__rep<N>` (the config's **`model`** field —
NOT `serve_name`, which differs on every q4 lane: `model: "qwen"` + `serve_name: "qwen4"` yields
`qwen__q4__…`; see `orchestrate.py::unit_id_for`; `q4`/`q5`/`mxfp4`/`iq4` for quant). Same string
is the `unit_id` field everywhere.

---

## 1. Task directory spec (COMPONENT 1 produces; graders + driver consume)

Every task is a self-contained dir: `tasks/<suite>/<task-id>/` with:

- `PROMPT.md` — the exact agentic instruction fed to `opencode run` (the ONLY thing the
  model sees, plus the `repo/` files it can read). Must be unambiguous and reference files
  by the paths they'll have inside the working copy (e.g. `src/solution.py`). Never mention
  `grade/`.
- `repo/` — the starting file tree copied into the model's working dir. For A: a stub to
  implement. For B: code containing planted bugs. For C: code + a `REVIEW.md` with comments
  (one deliberately wrong "noise" comment). For D: `source/` doc(s) to summarize/analyze.
- `grade/` — hidden from the model. Contents depend on `grader` (see §2). Never copied into
  the working dir.
- `meta.json` — schema below.

### meta.json schema
```json
{
  "id": "A1_events_transform",
  "suite": "A_coding",
  "title": "one-line human title",
  "grader": "pytest",                  // "pytest" | "review" | "diff_pytest" | "judge"
  "timeout_s": 900,                    // per-attempt hard cap (orchestrator enforces)
  "est_ctx_tokens": 6000,              // rough input size, for scheduling sanity
  "entrypoint": "src/solution.py",     // the file(s) the model must end up producing/editing
  "grade": { ...grader-specific, see §2... }
}
```

### Suite requirements (Python, pytest-first)
- **A_coding** — 14 tasks. Round 1: 3 tasks + **1 HumanEval+-style** task (4 total); round 2
  added `A5`–`A14`, BigCodeBench-derived. Model implements from a
  spec/stub. Grader = `pytest`. Themes: a pandas/polars data-transform, a data-validation
  function, a small pure-Python algorithm; the HumanEval+-style one is a classic function
  with a strong hidden test set. Each `grade/` has a `test_*.py` that imports the model's
  `entrypoint`. Tests must be deterministic (fixed seeds, no network, no clock).
- **B_review** — 6 tasks (`B6_control_nobugs` is the exception: it plants nothing — see §2).
  `repo/` has a module with a **known planted-bug key**. Model is
  asked (in PROMPT.md) to review and list bugs as a specific machine-parseable format (see
  review_grader §2). `grade/key.json` lists each planted bug with: `id`, `location` (file +
  line range), `synonyms` (accepted phrasings), `severity`. Grader scores recall + precision.
- **C_edit** — 5 tasks. `repo/` has working-ish code + `REVIEW.md` with review comments,
  **at least one of which is a deliberate wrong/noise comment** (documented in `grade/meta`).
  Model applies the valid fixes and should NOT act on the noise comment. Grader = `diff_pytest`:
  re-run hidden pytest (correctness) AND check the noise comment was ignored (diff inspection).
  (Round 1 authored exactly one; the `{"noise": [...]}` wrapper blessed in §2 made several legal
  and `C5_contradiction` ships two, so the authoring rule here is deliberately relaxed to "at
  least one" rather than left contradicting §2.)
- **D_text** — 6 tasks. Round 1: (1) summarize a real long tech doc in `source/` → key-point
  recall; (2) "give 3 approaches to X with tradeoffs" → rubric. Round 2 added the long-context
  probes `D3`/`D4`/`D5` and `D6_pr_describe`. Grader = `judge` (Opus, offline, not
  automated here). `grade/rubric.md` + `grade/key_points.json` for the summary. Driver just
  saves the model's answer; scoring is Opus's Stage-3 job.

Keep every task **small (<~30K ctx)** so per-config context caps never bite. The only exception
is the round-2 long-context probe series, which exists precisely to push against those caps:
`est_ctx_tokens` is 32,609 for `D3_longctx_30k`, 64,027 for `D4_longctx_60k` and 105,076 for
`D5_longctx_100k`.
Author reference solutions and RUN the pytest against them so tests are known-green on truth.

---

## 2. Graders (COMPONENT 2) — each is a standalone `uv run` CLI

Common CLI shape (all graders):
```
uv run graders/<g>.py --task <taskdir> --run <rundir> --out <path.json>
```
- `--task` = the `tasks/<suite>/<id>/` dir (read `grade/`, `meta.json`).
- `--run`  = the per-unit working dir the driver produced (contains the model's edited
  `repo/` copy at `<rundir>/repo/` and the driver's saved outputs at `<rundir>/driver.json`,
  `<rundir>/answer.txt`, `<rundir>/transcript.json`).
- Writes a JSON verdict to `--out` and also echoes it to stdout. **Exit 0 even on a failing
  grade** (a failed task is data, not a script error); exit non-zero only on grader malfunction.

### pytest_grader.py  → verdict schema
Copies the task's `grade/test_*.py` into a throwaway `tempfile.TemporaryDirectory` outside the
run dir (so `<rundir>/repo/` keeps reflecting only the model's own edits, which `diff_grader.py`
depends on) with `PYTHONPATH=<rundir>/repo`, runs
`pytest -q --tb=short --junitxml=<tmp>/junit.xml` and parses that JUnit XML with stdlib
`xml.etree.ElementTree` — deliberately, so no pytest-json plugin is needed — deterministically.
```json
{
  "grader": "pytest",
  "passed": 7, "failed": 1, "errors": 0, "total": 8,
  "pass_rate": 0.875,
  "failure_class": null,        // "no_file"|"import_error"|"syntax_error"|"timeout"|"assertion"|null
  "duration_s": 3.4,
  "detail": "1 failed: test_empty_input"
}
```
`meta.grade.requires` (a list of third-party packages; non-empty in 9 of the 31 task `meta.json`,
all of them A_coding tasks needing pandas/numpy/matplotlib/scipy/scikit-learn/pytz) switches the
grader from running pytest under its own interpreter (`sys.executable -m pytest`) to an ephemeral
`uv run --no-project --with pytest --with <pkg> … -- pytest`. Either path is capped at
`PYTEST_TIMEOUT_S` (120s in `pytest_grader.py`); exceeding it yields `failure_class: "timeout"`
with no collected results.

### review_grader.py  → verdict schema
Parses the model's answer (`<rundir>/answer.txt`) for bug findings in the format PROMPT.md
mandates (COMPONENT 1 must define one machine-parseable format, e.g. a JSON block or
`- [file:line] description` bullets — document it in the task's PROMPT.md and mirror the
parser here). Match findings against `grade/key.json` via location overlap + synonym match.
```json
{
  "grader": "review",
  "planted": 3, "found": 2, "hallucinated": 1,
  "recall": 0.667, "precision": 0.667,
  "matched_ids": ["b1","b3"], "missed_ids": ["b2"],
  "ambiguous": [ {"finding": "...", "closest_id": "b2"} ]   // for Opus adjudication
}
```
`ambiguous` = findings that partially matched; Opus resolves later, so SAVE them, don't guess.

**Round 2 addition — control tasks (e.g. `B6_control_nobugs`, on disk since Phase 4):**
`grade/key.json` plants nothing, recognised via an explicit `{"control": true, "bugs": []}`
(a bare `{"bugs": []}` is also honoured). `planted` is then 0, so `recall` is `null` — never
`0.0`, recall is undefined when nothing was planted. `precision` collapses to the
control-specific rule (any finding on a no-bug file is a false positive): `1.0` if the model
reported nothing, else `0.0`. The verdict additionally gains `false_positive_rate` (findings
count ÷ 1), present **only** for control-task verdicts — non-control verdicts keep exactly
the schema above.
```json
{
  "grader": "review",
  "planted": 0, "found": 0, "hallucinated": 2,
  "recall": null, "precision": 0.0,
  "matched_ids": [], "missed_ids": [], "ambiguous": [],
  "false_positive_rate": 2.0             // control tasks only
}
```

### diff_grader.py  → verdict schema (for C_edit; pairs with pytest_grader)
Computes `git diff` (or difflib) between task `repo/` (original) and `<rundir>/repo/` (edited):
```json
{
  "grader": "diff",
  "files_touched": 2, "lines_added": 9, "lines_removed": 3,
  "touched_expected_only": true,       // did it edit only files it was asked to?
  "noise_comment_acted_on": false,     // C_edit: did it wrongly follow the noise comment?
  "surgical_score": 0.9                 // 1.0 = minimal; penalize over-editing
}
```
For C_edit the orchestrator runs BOTH pytest_grader and diff_grader and merges (schema §4).

**Round 2 addition — `noise.json` gains a `kind` field** (`out_of_scope` | `already_done` |
`contradiction` | `must_survive`; `must_survive` is today's only kind, now explicit) and may
carry multiple entries via `{"noise": [...]}` (e.g. `C5_contradiction`, `C3_scope_creep`,
`C4_already_done` — on disk since Phase 4). A `noise.json` with no `kind` key (today's
only real shape, e.g. C1/C2) is untouched and byte-identical to before this addition. Which
`grade/noise.json` key each `kind` pairs with:
- `must_survive` / `already_done` → `required_pattern`/`required_snippet` (correct code that
  must remain untouched; `acted_on` == it is now ABSENT).
- `out_of_scope` → `forbidden_pattern`/`forbidden_snippet` (code that must NOT appear;
  `acted_on` == it is now PRESENT).
- `contradiction` → not diff-gradable at all (see below); `acted_on` is always `null`.

When `noise.json` opts into the new schema (has `kind` and/or the `{"noise": [...]}`
wrapper), the verdict's `noise_comment_acted_on` becomes an aggregate (`true` if ANY entry
was acted on, so existing consumers of that key keep working) and the verdict gains a
`noise` list, one entry per noise comment:
```json
{
  "grader": "diff",
  "files_touched": 1, "lines_added": 1, "lines_removed": 3,
  "touched_expected_only": true,
  "noise_comment_acted_on": true,        // aggregate: true if ANY entry below was acted on
  "surgical_score": 0.7,
  "noise": [
    {"kind": "must_survive", "file": "src/x.py", "acted_on": true},
    {"kind": "out_of_scope", "file": "src/x.py", "acted_on": false}
  ]
}
```
`contradiction` is the one noise kind a diff cannot grade: whether the model SURFACED the
conflict between two contradicting review comments lives in prose (`<rundir>/answer.txt`),
not in the tree. For that kind the grader instead reads `answer.txt` and reports
`conflict_surfaced: true|false|null` (null if `answer.txt` is missing) via a case-insensitive
substring match against `grade/noise.json`'s `conflict_signal.answer_must_mention`, tagged
`conflict_signal_kind: "keyword_match"` — reported honestly as WEAKER evidence than the
diff-based checks above, never presented as equivalent:
```json
{"kind": "contradiction", "file": "src/x.py", "acted_on": null,
 "conflict_surfaced": true, "conflict_signal_kind": "keyword_match"}
```

---

## 3. opencode_driver.py (COMPONENT 2) — runs one (task × model) attempt

```
uv run opencode_driver.py \
  --task <taskdir> --model <opencode-model-id> --agent <agent-name> \
  --run <rundir> --effort high --timeout <s> --out <rundir>/driver.json
```
Behavior:
1. Fresh `<rundir>/repo/` = copy of `tasks/<suite>/<id>/repo/` (never the grade dir).
2. Run OpenCode headless with cwd `<rundir>/repo/`:
   `opencode run "<contents of PROMPT.md>" --model <id> --agent <agent> --auto`
   Force **high reasoning effort** — determine the correct knob (per PLAN §8/§10.3): a CLI
   flag, an `--agent` whose config sets it, or an env/opencode.json field. **Verify against
   the live OpenCode/Studio setup and record which knob you used in driver.json.**
3. Capture the session id from the run; then `opencode export <sid>` → save raw to
   `<rundir>/transcript.json`. Save the final assistant answer text to `<rundir>/answer.txt`.
4. Enforce `--timeout`: kill the run if exceeded; record `status:"timeout"`.
5. Emit `driver.json`:
```json
{
  "unit_partial": {"model": "...", "agent": "...", "effort": "high"},
  "effort_knob": "how high-effort was set (documented)",
  "status": "completed",       // completed|timeout|error|stalled|infinite_loop
  "turns": 12,
  "wall_s": 84.2,
  "ttft_ms_per_turn": [1900, 2100, ...],
  "decode_tps_per_turn": [88.1, 79.4, ...],   // best-effort from export timings; null ok
  "tokens": {"think": 3400, "answer": 900, "prompt_total": 21000},
  "think_answer_ratio": 3.78,
  "tool_calls": {"total": 9, "malformed": 0},
  "termination": "clean",      // clean|hit_timeout|no_tools|xml_leak|loop
  "session_id": "...",
  "repo_dir": "<rundir>/repo",
  "answer_file": "<rundir>/answer.txt"
}
```
Fields that can't be extracted → `null`, never omit the key. The driver does NOT grade.

---

## 4. Per-unit result JSON (COMPONENT 3 assembles; §0 filename)

The orchestrator merges driver + grader(s) + RAM sampling into ONE atomic file per unit:
```json
{
  "unit_id": "qwen__q5__A_coding__A1_events_transform__rep1",
  "model": "qwen", "quant": "q5", "opencode_model_id": "unsloth/Qwen3.6-35B-A3B-MTP-GGUF",
  "suite": "A_coding", "task": "A1_events_transform", "rep": 1,
  "effort": "high",
  "driver": { ...driver.json... },
  "grade": { ...grader verdict(s); for C_edit: {"pytest": {...}, "diff": {...}} ... },
  "ram": {"rss_peak_gb": 22.1, "free_gb_min": 6.3, "sampled_at_ctx_tokens": 40000},
  "served": {"serve_name": "qwen", "real_ctx": 90112, "port": 8888},
  "started_ts": "<iso, injected by orchestrator>", "duration_s": 88.0,
  "schema_version": 1
}
```
Written only on completion (atomic: temp file + rename). Also append one line to
`results/manifest.jsonl`: `{"unit_id": "...", "status": "...", "pass_rate": ..., "ts": "..."}`.

---

## 5. configs.json + orchestrate.py (COMPONENT 3)

### configs.json (generate from PLAN §2 + `~/bin/unsloth-serve` — read the actual cases)
Array of config objects; the orchestrator's outer loop:
```json
[
  {
    "model": "qwen", "quant": "q5",
    "serve_name": "qwen",                       // arg to ~/bin/unsloth-serve
    "opencode_model_id": "unsloth/Qwen3.6-35B-A3B-MTP-GGUF",
    "real_ctx": 90112, "probe_max_ctx": 80000,  // min(80000, real_ctx)
    "mtp": true, "reasoning": "on",
    "broken": false
  },
  { "model": "qwen", "quant": "q4", "serve_name": "qwen4", ... },
  ...all ~15 configs from PLAN §2, both quants where they exist...
]
```
Read the real `-c` per case out of `~/bin/unsloth-serve`; don't hardcode from memory.

### orchestrate.py behavior (the resumable engine)
```
uv run orchestrate.py --resume [--stage 1|2] [--only <model>] [--dry-run]
```
Outer loop over `configs.json`; for each config:
1. **Skip-if-done:** for every planned unit `(config, suite, task, rep)`, if
   `results/<unit>.json` exists → skip. If ALL its units exist → don't even serve it.
2. **Serve:** `~/bin/unsloth-serve <serve_name>` (background); **wait-for-ready** by polling a
   1-token `POST :8888/v1/chat/completions` until it returns 200 — **not** `GET :8888/v1/models`,
   which answers the instant Studio binds the port but before the weights are loaded; requests
   fired into that gap 400 and falsely marked both qwen quants broken on 2026-07-12 (see
   `orchestrate.py::wait_for_ready`); **zombie-check** (Studio silent :8889 rebind / 502 parent-zombie —
   see `setup/UNSLOTH-CHEATSHEET.md`); abort this config cleanly if it
   won't come up (mark units `broken`, continue).
3. **Speed probe:** `uv run speed_probe.py --model <id> --max-ctx <probe_max_ctx> --rounds 3
   --out results/probe__<model>__<quant>.json`.
4. **Smoke:** run the existing `../bench/smoke_test.py` (or its 6-scenario logic) → if 0 tools
   / garbage → mark config `broken`, skip the 3× quality depth (speed probe already captured).
5. **Tasks:** for each `(suite, task, rep)` per stage schedule (Stage 1 = rep1 only; Stage 2 =
   rep2,rep3): `opencode_driver.py` → grader(s) → sample RAM mid-run (`ps`/`memory_pressure`,
   store peak RSS + min free) → assemble unit JSON (§4) → atomic write → manifest append.
   Enforce each task's `timeout_s`.
6. **Unload** (Studio one-model-at-a-time) before the next config; verify RAM released.

Determinism/safety: idempotent; a crash mid-config loses at most the in-flight unit; per-task
timeouts so a hung model can't stall the run; every raw output saved so grading is re-runnable
without re-inferring. **Sonnet subagents (high effort, not xhigh)** are invoked BY the human
operator (Opus) for judgement/mess (broken-vs-retry calls, sharded-GGUF assembly, per-model
narrative) — the engine itself is pure Python and needs no LLM on the happy path.

`--dry-run` = do everything except actually launch models: validate configs.json, that every
task dir parses, that graders import, that `unsloth-serve` has each case, that opencode ids
resolve. Must pass before any real launch.

---

## 6. What each component returns to the orchestrator (Opus)

Keep your final message SHORT (it's a status, not a file dump): list files created, any
interface point where you deviated + why, and the ONE command to smoke-test your component in
isolation. Do not paste full file contents back.
