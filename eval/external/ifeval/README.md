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
- `max_tokens=1280`.
- `--strip-reasoning {auto,on,off}` (default `auto`): strips `<think>…</think>` /
  `<reasoning>…</reasoning>` / `<thinking>…</thinking>` out of `choices[0].message.content`.
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
    answer within 1280 tokens" rather than mistaken for "it ignored every instruction."
  - Unit coverage: `uv run eval/external/ifeval/test_strip_reasoning.py` — well-formed pair,
    unclosed tag (→ empty), no tags (→ unchanged), tags mid-response, `off` mode, `auto`≡`on`,
    a closed pair followed by a second unclosed tag (keeps the real answer, drops the truncated
    tail), and a separate `reasoning_content` field (recorded, not required to strip anything).
- Serve lifecycle (`serve_config` / `unload`) is **imported from `harness/orchestrate.py`**, not
  reimplemented. Requires `eval/harness/ops/serving_mode.sh eval` to have handed `:8888` to the
  eval harness first — `run_ifeval.py` refuses to launch (aborts loudly, names the script to run)
  if `:8888` is still held by `llama-swap`.
- Resumable **per prompt**: every attempt (success or error) is appended immediately to
  `_work/<model>__<quant>.jsonl` (gitignored), so a crash or usage-limit stop loses at most one
  in-flight prompt. `n_errors` in the result JSON counts request failures — without it, a
  transport error is indistinguishable from a model genuinely failing every instruction on that
  prompt (the same argument BigCodeBench's `n_env_errors` makes).

## Repro commands

```bash
# Live acceptance (one config, 20 prompts) — needs `serving_mode.sh eval` run first
uv run eval/external/ifeval/run_ifeval.py --only opus --limit 20

# Full 541-prompt run for one model (both quants, since --only filters on "model" not "quant")
uv run eval/external/ifeval/run_ifeval.py --only opus

# Every non-broken config in harness/configs.json
uv run eval/external/ifeval/run_ifeval.py

# Offline re-score from a saved generations file — no server, no model, ever re-runnable
uv run eval/external/ifeval/run_ifeval.py \
  --score-only eval/external/ifeval/fixtures/synthetic_responses.jsonl \
  --model synthetic --quant test --out /tmp/ifeval_synthetic_test.json
```

Output → `eval/results/ifeval__<model>__<quant>.json` (schema: see `run_ifeval.py`'s
`score_and_build()` or IMPLEMENTATION_PLAN.md §5).

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
