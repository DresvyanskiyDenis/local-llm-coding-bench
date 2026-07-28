# IFEval — instruction-following adapter

**Lane 2** (IMPLEMENTATION_PLAN.md §3): this does **not** go through OpenCode. It measures the
*model*, not the harness — single-turn, no system prompt, no agent, no tools, straight to
`POST /v1/chat/completions`.

## What IFEval is

Zhou, Lou et al., *Instruction-Following Evaluation for Large Language Models*
([arXiv:2311.07911](https://arxiv.org/abs/2311.07911)), Google Research. 541 prompts, each
tagged with one or more of 25 programmatically-verifiable instructions (word/sentence/paragraph
counts, casing, JSON formatting, keyword inclusion, language, bullet lists, quotation wrapping,
…). No LLM judge: every instruction is checked by deterministic Python, which is exactly why it
is used here — a grader nobody in this project wrote.

### The four metrics

For each response, every instruction it was tagged with is checked twice — **strict** (checked
against the raw response) and **loose** (checked against 8 lightly-normalized variants: with/
without the first line, the last line, both, and with/without `*` — an upper bound that tolerates
markdown wrapping or a stray leading/trailing line without calling it a miss). Each check is then
rolled up two ways:

| Metric | Meaning |
|---|---|
| `prompt_level_strict` | fraction of prompts where **every** tagged instruction passed (strict) — **the headline number** |
| `inst_level_strict` | fraction of **individual instruction checks** that passed (strict) — finer-grained than prompt-level |
| `prompt_level_loose` | same as prompt-level, loose variant |
| `inst_level_loose` | same as instruction-level, loose variant |

`by_instruction_type` breaks `inst_level_strict` down per full instruction id (e.g.
`length_constraints:number_words`, `punctuation:no_comma`) — this is not decoration, it is what
turns "qwen is bad at formats" into "qwen fails *these* format classes."

## Why not `lm-evaluation-harness`

`lm-eval` ships an IFEval task, but it declares `torch>=1.8` as a **core** dependency (not an
optional extra) — unwanted on this machine, which serves GGUFs directly and has deliberately
avoided a torch install for the entire eval stack. Vendoring google-research's own
`instruction_following_eval` package directly avoids that dependency entirely: the four files it
takes are pure Python + `nltk`/`langdetect`/`absl-py`/`immutabledict`.

## Vendored, unmodified

`vendor/instruction_following_eval/` is the upstream package, byte-identical — see
`vendor/PROVENANCE.md` for URLs, fetch date and per-file sha256. **Do not edit anything under
`vendor/` or `data/`** — modifying a vendored grader forfeits the entire point of this round.
`run_ifeval.py` imports `evaluation_lib.test_instruction_following_strict` /
`test_instruction_following_loose` / `read_prompt_list` / `read_prompt_to_response_dict` and
never reimplements the constraint checkers or the strict/loose response-variant logic.

`data/input_data.jsonl` — 541 prompts, sha256
`67ffeee0fcb87c317c5b08a2de85557b4a7e96ada6178aa645b4954fe4b53d49` (recorded in `vendor/PROVENANCE.md`).

## NLTK data

`instructions_util.py:135` (vendored, unmodified) calls
`nltk.data.load("nltk:tokenizers/punkt/english.pickle")` for every
`length_constraints:number_sentences` check. nltk ≥3.10 sandboxes file access to `NLTK_DATA` /
`nltk.data.path`, so `run_ifeval.py` sets `NLTK_DATA` to the repo-local `nltk_data/` **before**
importing anything that transitively imports `nltk`. If `nltk_data/` is empty or missing:

```bash
uv run eval/external/ifeval/bootstrap_nltk.py
```

## Generation contract

- **No system prompt** — a system prompt would contaminate an instruction-following measurement.
- **Explicit neutral sampling on every request**, sent verbatim, never relying on server
  defaults: `temperature=0, top_p=1, top_k=0, min_p=0, presence_penalty=0, frequency_penalty=0`
  (IMPLEMENTATION_PLAN.md §3.5 bite 3 — per-model server defaults differ across this fleet and a
  penalty of 1.5 on an IF-following measurement would be a real, uneven distortion).
- `max_tokens=4096` (raised from the phase-1 default of `1280` — see "Why the cap moved to
  1280 → 4096" below; this is unresolved-but-adopted, not a settled measurement).
- `--strip-reasoning {auto,on,off}` (default `auto`): strips `<think>…</think>` /
  `<reasoning>…</reasoning>` / `<thinking>…</thinking>` out of `choices[0].message.content`,
  plus two further shapes ported from `eval_proxy.py` — an orphan closing `</think>` with no
  opening tag, and gpt-oss's closed harmony analysis channel. See "The two strippers, diffed"
  below for what each side covers, what the orphan-close pattern costs, and what still leaks.
  **The leak is confirmed, not hypothetical** — `eval/external/reasoning_leak_probe.json` (a
  live probe against `qwen4`) shows `choices[0].message` keys are exactly
  `['content', 'refusal', 'role']`: no `reasoning_content`, no `reasoning` field,
  `usage.completion_tokens_details.reasoning_tokens` is `0`, and `content` begins with a literal
  `<think>`. There is no separate field to prefer instead of stripping; `auto` and `on` both
  resolve to stripping (kept as two CLI names for clarity — `auto` is the recommended default).
  `off` disables stripping entirely, for deliberately measuring the raw leak.
  - **Truncation**: a thinking model can spend its entire `max_tokens` budget on reasoning and
    return `finish_reason: "length"` with an *opening* `<think>` and no closing tag — the whole
    visible response is then unterminated reasoning, never an answer. The stripper detects an
    unclosed tag after the well-formed-pair pass and discards it and everything after it,
    yielding an **empty** response rather than leaking raw chain-of-thought into the scored
    text. An empty response then legitimately fails every instruction — correct scoring, not a
    bug — but it must be visible: the result JSON carries `n_finish_length` (requests that hit
    the token budget) and `n_empty_after_strip` (responses that came out empty post-stripping),
    so a near-zero `prompt_level_strict` on a thinking config can be read as "it never reached an
    answer within the `max_tokens` budget" rather than mistaken for "it ignored every instruction."
  - Unit coverage: `uv run eval/external/ifeval/test_strip_reasoning.py` — well-formed pair,
    unclosed tag (→ empty), no tags (→ unchanged), tags mid-response, `off` mode, `auto`≡`on`,
    a closed pair followed by a second unclosed tag (keeps the real answer, drops the truncated
    tail), a separate `reasoning_content` field (recorded, not required to strip anything), an
    orphan closing `</think>` (monologue removed, answer kept) and the cost of that pattern
    (ordinary prose containing a bare `</think>` loses its opening — asserted, see below), the
    harmony analysis channel closed *and* truncated (the truncated half asserts the current,
    unflagged behaviour), and the untagged-leak gap documented below (asserts current, imperfect
    behaviour — not a claim it is correct).
  - **Verdict on the specific question this test suite exists to answer**: a response cut off
    mid-`<think>` (unclosed tag, `finish_reason: "length"`) strips to **EMPTY**, not to the
    partial reasoning text — confirmed by `test_strip_reasoning.py`'s second case, 8/8 (now
    12/12) passing. That mechanism is correct. See "Reasoning leak: a second, untagged shape"
    and "The two strippers, diffed" below for real, live gaps in *different* leak shapes it does
    not cover.
- Serve lifecycle (`serve_config` / `unload`) is **imported from `harness/orchestrate.py`**, not
  reimplemented. Requires `eval/harness/ops/serving_mode.sh eval` to have handed `:8888` to the
  eval harness first — `run_ifeval.py` refuses to launch (aborts loudly, names the script to run)
  if `:8888` is still held by `llama-swap`.
- Resumable **per prompt**: every attempt (success or error) is appended immediately to
  `_work/<model>__<quant>.jsonl` (gitignored), so a crash or usage-limit stop loses at most one
  in-flight prompt. `n_errors` in the result JSON counts request failures — without it, a
  transport error is indistinguishable from a model genuinely failing every instruction on that
  prompt (the same argument BigCodeBench's `n_env_errors` makes).
- **Endpoint is `http://127.0.0.1:8888/v1` — the server directly, NOT `:8899` (`eval_proxy.py`)**.
  See "Endpoint: why this bypasses `eval_proxy`" below for why that's a deliberate, documented
  choice and not an oversight.

### Reasoning leak: a second, untagged shape the stripper does not catch

The gate run (`eval/results/ifeval__opus__q4.json`, `opus/q4`, 20 prompts) showed
`n_finish_length: 15` next to `n_empty_after_strip: 0` — every truncated response came back
non-empty. Inspecting the actual generations (`_work/opus__q4.jsonl`, gitignored) shows why: for
this config (`hesamation/Qwen3.6-35B-A3B-Claude-4.6-Opus-Reasoning-Distilled-GGUF`), **13 of the
15 length-truncated responses are unterminated reasoning prose with no `<think>` tag at all** —
e.g. key 1000 (5491 chars) opens `"Thinking Process:\n\n1. **Analyze the Request:**\n    *
Topic: ..."` and never reaches an answer before the (then-)1280-token budget runs out.
`REASONING_TAG_RE`/`OPEN_REASONING_TAG_RE` are both tag-anchored (`<think>`/`<reasoning>`/
`<thinking>`) and never fire on this shape, so **the raw monologue passes straight through and
is scored as the model's answer** — silent corruption of the 15 affected prompts'
`prompt_level_strict`/`inst_level_strict`, via a leak shape the phase-0 probe (qwen4, tagged
`<think>`) never surfaced. `test_strip_reasoning.py`'s last case reproduces this exact string and
asserts the current (undesired) pass-through behaviour, so it is provable rather than inferred.

Two things worth knowing before drawing conclusions from this:
- All 5 responses in that same run that finished with `finish_reason: "stop"` had **zero**
  reasoning preamble — clean answers only. That's suggestive (more token budget may turn
  truncated-mid-monologue responses into ordinary clean stops rather than the model rambling
  regardless of cap) but is not proof; it's one config, 20 prompts.
- `eval_proxy.py` (`:8899`, owned by the port owner / used by BigCodeBench) has the **same
  untagged-prose gap** — its `strip_reasoning()` is tag-anchored too (`<think>`, harmony
  `<|channel|>analysis`). This is not an IFEval-only problem; any config that leaks reasoning as
  untagged prose is unprotected on both paths. Flagging this for the team, not fixing
  `eval_proxy.py` here — it's out of this round's scope (owned by another agent) and a fix needs
  to be consistent across both files, not adapter-local. What is shared is this *gap*, not the
  implementations: outside it the two are **not** at parity — see the diff below.

**Not fixed in this change.** Inventing a detection heuristic for untagged prose (e.g. matching
on `"Thinking Process:"` or similar headings) risks false-positives against legitimately
structured answers (the vendored checker scores headings, numbered lists, and markdown
structure directly — `detectable_format:*`, `length_constraints:*` — so a heuristic strip could
itself corrupt scoring for a different set of prompts). This needs a decision, not a guess:
either a per-model-family leak probe (like the phase-0 `<think>` one) before trusting any
untagged-reasoning config's numbers, or a cross-file (`run_ifeval.py` + `eval_proxy.py`) design
for it. Treat `opus/q4`'s `prompt_level_strict: 0.25` from the gate run as **not yet
trustworthy** until this is resolved.

### The two strippers, diffed

`run_ifeval.py` talks to `:8888` directly, so `eval_proxy.py` is never in the path and this lane
carries its own copy of the patterns. They are separate on purpose (one rewrites a live HTTP
body, the other rewrites a saved record) and they have drifted. What each side handles now:

- **Closed pair.** `run_ifeval.py`'s `REASONING_TAG_RE` matches `<think>`, `<reasoning>` *and*
  `<thinking>`; `eval_proxy.py`'s `THINK_BLOCK` matches `<think>` only.
- **Unclosed opening tag (truncation).** Same asymmetry — `OPEN_REASONING_TAG_RE` covers all
  three spellings, `THINK_UNCLOSED` covers `<think>`. This lane additionally returns a
  per-response `truncated` flag (it drives the `TRUNCATED` log line and pairs with
  `n_empty_after_strip`); the proxy has no truncation-specific flag — it records
  `empty_after_strip` / `empty_finish_reasons` per request in its JSONL and a process-wide total
  on shutdown, which does not separate truncation from any other strip that empties a choice.
- **Orphan closing tag** — a monologue that ends in `</think>` with no opening tag, because the
  chat template opened the block in the prompt prefix and it is never echoed back.
  `ORPHAN_CLOSE_RE` is `eval_proxy`'s `ORPHAN_CLOSE` verbatim, `<think>`-only on purpose: the
  proxy's own rule is that a delimiter must be *observed* before it is stripped.
- **gpt-oss harmony analysis channel.** `HARMONY_ANALYSIS_RE` is `eval_proxy`'s
  `HARMONY_ANALYSIS` verbatim.
- **Untagged reasoning prose.** Neither catches it — the gap above.

So the asymmetry is: tag *spellings* (three here, one there) and truncation *reporting* (a
dedicated `truncated` flag here, only emptiness-after-strip there). The other two shapes are verbatim ports. Keeping them in
step is a manual job in both directions.

**Still a gap in both files: a truncated harmony monologue is neither stripped nor flagged.**
`HARMONY_ANALYSIS_RE` only matches a *closed* analysis channel (terminated by `<|end|>` or the
final-channel marker). A monologue cut off by the token cap carries neither, so nothing matches,
the raw monologue is scored as the answer — **and** `truncated` stays `False`, because that flag
is bound to the unclosed-`<think>` branch alone. `n_empty_after_strip` misses it too — that
counts responses left *empty* after stripping, and this one comes through non-empty; only
`n_finish_length` sees it at all, and it cannot tell it apart from an ordinary long answer.
Concrete exposure: `gpt-oss/mxfp4` is **not** marked `broken` in
`harness/configs.json`, so a plain run scores it, and this is its most likely failure mode at
`max_tokens=4096`. Pinned as the `cut` half of `test_strip_reasoning.py`'s last case — stated,
not fixed; the fix needs an observed sample first.

**And a cost, not a gap: `ORPHAN_CLOSE_RE` is `\A`-anchored** and deletes everything up to the
first bare closing tag. In the BigCodeBench lane a mangled response at least lands somewhere
observable — `sanitize()` + `ast.parse()` turn it into a counted `n_unparseable_solutions`
(`run_bcb.py`'s `completion_stats()`); **IFEval scores free text**, so an ordinary answer that
merely mentions `</think>` loses its opening — a real false positive, not a theoretical one.
Pinned as its own case in
`test_strip_reasoning.py` ("COST OF THE ORPHAN-CLOSE SHAPE"), which asserts that
`"Some models emit </think> to close a reasoning block. Never nest them."` scores as
`"to close a reasoning block. Never nest them."` The trade-off is deliberate: the shape the
pattern catches was observed in a real sample, and this is its price.

### Why the cap moved to 1280 → 4096

Same gate run, same evidence: 13/20 prompts spent the *entire* 1280-token budget on reasoning
prose and never reached an answer — `prompt_level_strict: 0.25` may be measuring "did the model
finish thinking in time" more than instruction-following. `4096` is the value the team already
planned to measure at (round-2 brief); this file adopts it as the new default ahead of that
measurement existing, on the strength of the above (key 1005 in the same run got to `## Final
Answer` at 2592 chars and was *still* cut off — clearly reasoning-budget-starved, not
content-starved).

**Trade-off, stated not resolved**: the 19.4 s/prompt rate the sizing table below is built on
was measured **at `max_tokens=1280`**. It does not hold at 4096 — expect it to rise, by an
unmeasured amount, specifically for reasoning-heavy configs (short, clean-stop answers are
unaffected either way). `--sample` size and `--max-tokens` compete for the same wall-clock
budget: raising the cap to fix truncation makes the "44 h doesn't fit" problem below worse, not
better. Pick a sample size *after* deciding the cap, or re-measure s/prompt at 4096 before
trusting the table's hour figures.

### Endpoint: why this bypasses `eval_proxy`

`generation.endpoint` is `http://127.0.0.1:8888/v1` — the llama-server directly, not
`eval_proxy.py` on `:8899`. `eval_proxy` exists because BigCodeBench's client
(`gen/util/openai_request.py`, `make_auto_request`) hardcodes `top_p=0.95` and accepts only a
handful of sampling kwargs, so the neutral-sampling override has to happen somewhere the client
can't reach: the proxy. **That constraint does not apply here.** `run_ifeval.py` builds its own
request body (`generate_one()`) and sends all six `NEUTRAL_SAMPLING` keys itself, verbatim, on
every request — there is no client-side limitation for a proxy to work around. Going through
`:8899` anyway would add a hop, a second reasoning-stripper implementation to keep in sync with
this file's (see "The two strippers, diffed" above — they already disagree on tag spellings and
on truncation reporting, and they'd need to stay in lockstep by hand), and no behavioural
benefit. Bypassing it is a
deliberate, model-serving-layer decision, not an oversight, and only holds for adapters that set
every sampling parameter themselves — it does not generalize to BigCodeBench.

## Sampling: `--sample` / `--seed` (for a night that fits)

Measured: 388 s / 20 prompts = **19.4 s/prompt** (`eval/results/ifeval__opus__q4.json`,
`wall_clock_s: 388.0`, at the phase-1 `max_tokens=1280` — see the trade-off note above, this
does not hold at 4096). The full suite: 541 × 19.4 s ≈ 2.91 h/config, × 15 configs ≈ **43.7 h** —
does not fit a night.

`--sample N` draws a **seeded, deterministic stratified subsample** of size N instead of the
full 541 (mutually exclusive with `--limit`, which just truncates the raw list — not
representative of the type distribution, dev-smoke-test only).

**What "stratified" means here, stated plainly rather than left in the code** (full detail:
`stratified_sample()` docstring in `run_ifeval.py`). Prompts carry *multiple* instruction ids
(`instruction_id_list`), so exact stratification is a set-cover problem, not a groupby. This
adapter groups prompts by their **primary id** (`instruction_id_list[0]`) only — 25 groups —
then allocates a per-group quota: a floor of 1 prompt per group (when N is large enough to give
every group one), then the remainder by each group's proportional share of the full 541,
apportioned by largest-remainder rounding so quotas sum to exactly N. Which prompts land in a
group's quota is decided by a seeded shuffle (`random.Random(seed)`, default seed
`20260101`, fixed and checked in — **not** derived from time/PID), so a given `--sample N`
reproduces the identical subset on every run. Non-primary instruction ids still ride along —
`by_instruction_type` in the output is computed over every instruction id actually present in
the sample, same as an unsampled run; only the *grouping/quota* logic looks at the primary id
alone.

**The result JSON always carries `n_prompts` alongside `n_prompts_available`** (541, the full
reference set, regardless of `--sample`/`--limit`), plus `sampled` (bool), `sample_requested_n`,
`sample_seed`, and `sample_realised_n_by_type` (the **realised count per primary instruction
type** — not its accuracy, that's still `by_instruction_type`) — so a subsampled score can never
be mistaken for a full-suite one, and a type left thin (e.g. `n=2`) is visible in the JSON
rather than something a reader has to infer from a suspicious `by_instruction_type` number.

### Sizing table (arithmetic only — pick N, don't infer it)

All rows at the **measured** 19.4 s/prompt (`max_tokens=1280` — re-measure if the cap moves to
4096, see above). `min`/`max` per-type are the *actual* realised counts from
`stratified_sample()` against the real 541-prompt set, default seed, not hand-estimated:

| N | per-config | × 15 configs | min n / type | max n / type |
|---:|---:|---:|---:|---:|
| 541 (full suite) | 2.91 h (174.9 min) | **43.7 h** | — (no stratification, everything) | — |
| 250 | 1.35 h (80.8 min) | 20.2 h | 4 | 18 |
| **148** | 0.80 h (47.9 min) | **12.0 h** | 2 | 11 |
| **99** | 0.53 h (32.0 min) | **8.0 h** | 2 | 7 |

`148` and `99` are the exact solutions to `N × 19.4 s × 15 = 12 h` / `8 h` respectively (rounded
to the nearest whole prompt: 148.45 → 148, 98.97 → 99) — not round numbers chosen for looks.
Both land with a `min n/type` of 2: several of the 25 instruction types (the smaller groups,
e.g. `detectable_format:multiple_sections` at 9 prompts total) will have only 2 realised
examples in either size — visible via `sample_realised_n_by_type` in the output, not hidden.
**Denis picks the size; this table is the arithmetic, not the decision.**

## Repro commands

```bash
# Live acceptance (one config, 20 prompts, NOT stratified — dev smoke test) — needs
# `serving_mode.sh eval` run first
uv run eval/external/ifeval/run_ifeval.py --only opus --limit 20

# Stratified subsample sized for a night that fits (see the sizing table above for the choice
# of N) — deterministic, same subset every run at the same N/seed
uv run eval/external/ifeval/run_ifeval.py --only opus --sample 148

# Full 541-prompt run for one model (both quants, since --only filters on "model" not "quant")
uv run eval/external/ifeval/run_ifeval.py --only opus

# Every non-broken config in harness/configs.json
uv run eval/external/ifeval/run_ifeval.py

# Offline re-score from a saved generations file — no server, no model, ever re-runnable
uv run eval/external/ifeval/run_ifeval.py \
  --score-only eval/external/ifeval/fixtures/synthetic_responses.jsonl \
  --model synthetic --quant test --out "$TMPDIR/ifeval_synthetic_test.json"
```

Output → `eval/results/ifeval__<model>__<quant>.json` (schema: see `run_ifeval.py`'s
`score_and_build()` or IMPLEMENTATION_PLAN.md §5). Round-2 additions to that schema:
`n_prompts_available`, `sampled`, `sample_requested_n`, `sample_seed`,
`sample_realised_n_by_type` (see "Sampling" above).

## Verification fixture (no model needed)

`fixtures/synthetic_responses.jsonl` — 21 real prompts from `data/input_data.jsonl`, hand-written
responses (14 designed to pass, 7 designed to fail), verified against the actual vendored checker
(not simulated). Covers the two paths that most need proving:

- **key 1174** exercises `length_constraints:number_sentences` — the constraint that calls
  `nltk.data.load(...)`, i.e. the one that would break first if `NLTK_DATA` weren't wired
  correctly.
- **key 1108** exercises `language:response_language` (`kn` / Kannada) — the `langdetect` path.

Re-run scoring over it any time with the `--score-only` command above; it produces all four
metrics populated and several instruction types strictly between 0.0 and 1.0 (not just pass/fail
extremes), e.g. `punctuation:no_comma: 0.25`, `change_case:english_lowercase: 0.75`.

### Determinism: two independent RNG sources had to be seeded, one is a vendor quirk worth knowing

`--score-only` over the identical, byte-unchanged fixture initially gave *different*
`prompt_level_strict`/`prompt_level_loose` on different processes. Two distinct causes, both
fixed adapter-side (in `run_ifeval.py`, not in `vendor/`):

1. `langdetect.detect()` builds a fresh `Detector` seeded from OS entropy on every call unless
   `DetectorFactory.seed` is set — affects `language:response_language` and both
   `change_case:english_capital/lowercase` checkers (they also assert `langdetect.detect(...) ==
   "en"`). Fixed with `langdetect.DetectorFactory.seed = 0`, upstream's own documented fix.
2. `keywords:letter_frequency`'s `build_description(letter=...)` (vendor `instructions.py`)
   only accepts a single a-z character; key 1122's real prompt (`data/input_data.jsonl`) asks
   for hashtag frequency with `letter: "#"` (ord 35, outside `[97, 122]`) — the checker silently
   treats this as "no letter given" and substitutes `random.choice(string.ascii_letters)` via
   Python's **global, unseeded `random` module**. Confirmed by direct instantiation: the same
   `build_description(letter="#", ...)` call resolves to a different `self._letter` on repeated
   calls. Fixed with `random.seed(0)` alongside the langdetect seed.

Seeding both RNGs makes a given process's scoring run fully reproducible — verified 8/8 runs
byte-for-byte identical (`ts`/`wall_clock_s` excepted) over this fixture. **What seeding does
not fix**: the real target letter `"#"` is already gone by the time `build_description` returns
— this is upstream vendored/dataset behavior, left untouched per the vendored-unmodified rule.
Any real model answering prompt key 1122 in the live 541-prompt set is scored against whichever
a-z letter this process's seeded RNG happens to draw, not against `#` — a fact worth knowing if
`keywords:letter_frequency` looks inconsistent between reruns using a *different* seed, or if
other prompts in the real dataset carry a non-a-z `letter` kwarg.
