# Provenance — the BigCodeBench-derived A_coding tasks (`A5`–`A14`)

`A1`–`A4` are hand-written and are **not** covered by this file. Everything below applies only
to the ten `A*_bcb*_*` task dirs, which are **derived from third-party content**.

Derivation script: `eval/harness/ops/wrap_bcb_tasks.py` (`--list` / `--emit` / `--verify`).
The task dirs are generated, not hand-edited — re-running `--emit` reproduces them byte-for-byte.

## Why these exist

Round-1 `A_coding` scored **0.883–0.994 across all 15 configs**: it separates nothing, yet it
carries the largest composite weight (0.35). BigCodeBench-Hard was already vendored for the
**external lane** (direct `/v1/chat/completions`, single turn, no agent). Wrapping the *same*
upstream tasks as ordinary in-harness A tasks makes A discriminating again **without** turning it
into a model benchmark: it stays a harness-level measurement, which is the question this project
actually asks ("which local setup should I run in OpenCode").

The design point is the pairing. One upstream task, two delivery modes:

| Lane | Delivery | Grader | Artifact |
|---|---|---|---|
| 1 | OpenCode, tools, multiple turns | `eval/harness/graders/pytest_grader.py` | `eval/results/<cfg>__A_coding__<task>__rep<N>.json` |
| 2 | endpoint, single turn, no agent | BigCodeBench's own executor | `eval/results/bcb__<cfg>.json` |

Lane 1 minus lane 2, same task and same assertions, **isolates the harness contribution**. The
machine-readable pairing is `BCB_PAIRING.json` in this directory — do not reconstruct it by hand
from directory names.

## Source

| Item | Value |
|---|---|
| Dataset | `bigcode/bigcodebench-hard`, split `v0.1.4` (148 tasks) |
| Dataset URL | <https://huggingface.co/datasets/bigcode/bigcodebench-hard> |
| HF dataset commit | `298d2cc7b96612e15e47313c3603ee124cee0c1f` (card `lastModified` 2025-02-23) |
| Local arrow read | `~/.cache/huggingface/datasets/bigcode___bigcodebench-hard/default/0.0.0/298d2cc.../bigcodebench-hard-v0.1.4.arrow` |
| arrow sha256 | `71903377d492038b3748a21bd97ff82976149b6bba8fb47da1b61277ce05c280` |
| Upstream repo | <https://github.com/bigcode-project/bigcodebench> |
| Harness package | `bigcodebench` 0.2.5 (see `../../external/bigcodebench/PROVENANCE.md`) |
| Paper | Zhuo et al., *BigCodeBench*, [arXiv:2406.15877](https://arxiv.org/abs/2406.15877) |
| Fetched | 2026-07-25 (by `../../external/bigcodebench/bootstrap.sh`) |
| Derived | 2026-07-26 |

Verify the dataset pin with:

```bash
shasum -a 256 ~/.cache/huggingface/datasets/bigcode___bigcodebench-hard/default/0.0.0/\
298d2cc7b96612e15e47313c3603ee124cee0c1f/bigcodebench-hard-v0.1.4.arrow
```

### License — what was actually checked

- **Apache-2.0.** Verified three ways: the upstream repo's `LICENSE`; the installed wheel's
  `bigcodebench-0.2.5.dist-info/METADATA` (`License: Apache-2.0`, plus the OSI classifier and a
  bundled `licenses/LICENSE`); and the parent dataset card `bigcode/bigcodebench`
  (`cardData.license == "apache-2.0"`, tag `license:apache-2.0`).
- **Gap, recorded rather than papered over:** the `bigcode/bigcodebench-hard` card carries **no**
  `license` field (`cardData.license` is `null`, no `license:*` tag) — checked against the HF API
  on 2026-07-26. `-hard` is a filtered subset of the same records as the parent, so Apache-2.0 is
  taken by inheritance. If a stricter answer is ever needed, it has to come from upstream.
- Apache-2.0 requires attribution and a statement of changes. That is what this file is; the
  "How each task was derived" section below is the statement of changes.

**The vendored BigCodeBench install and the HF cache are read-only here.** Nothing upstream was
patched, and no file under `eval/external/bigcodebench/` was modified by this work.

## The ten tasks

| Harness task (lane 1) | Upstream id (lane 2) | Upstream tests | `grade.requires` | source record sha256 |
|---|---|---|---|---|
| `A5_bcb854_permutation_factorials` | BigCodeBench/854 | 5 | — | `0de1c514468ed7dbf42e990ce6c37617394577e2db4055af838585da390321ec` |
| `A6_bcb928_bigram_frequency_table` | BigCodeBench/928 | 5 | — | `dbb2f4bb004a1ab3d209a6efb21cbabd4e22ed04b687a462720d842b48426b21` |
| `A7_bcb458_json_doubling_dataframe` | BigCodeBench/458 | 5 | pandas | `8795155df42f98dfe01e094a67aa89ad6579981b0a87accaf1ad38ed46531afb` |
| `A8_bcb870_tuple_position_means` | BigCodeBench/870 | 5 | numpy, pandas | `735f2ff7a02da3e22ef74ea006585ecc4c2460b95108b5e3fd79b1673a33eed4` |
| `A9_bcb513_fitness_column_stats` | BigCodeBench/513 | 12 | matplotlib, numpy, pandas | `5e7fe87e7cf01533b7dee14ba82be4c8e1fe61ebd0aa70a53efd291bd6e8a9b9` |
| `A10_bcb1077_timezone_mean_gap` | BigCodeBench/1077 | 6 | numpy, pytz | `f68c31f9b4a2263e5fcfd49f3f142c701f8be16088676f5262eba11985e8221e` |
| `A11_bcb969_minmax_cumsum` | BigCodeBench/969 | 7 | numpy, pandas, scikit-learn | `c871c5b1f054f449445f4f684d23d7ad6300a845145d8acaf822114c174ad84b` |
| `A12_bcb532_duplicate_histogram_norm` | BigCodeBench/532 | 6 | matplotlib, numpy, pandas, scipy | `002993064b80f14db4fa61b9e0cc6a293baafcd2a932437f603dc722d99e6549` |
| `A13_bcb139_numeric_column_histograms` | BigCodeBench/139 | 7 | matplotlib, numpy, pandas | `a17569baab02ddc3dbbe8c55fc2c021920ddb2731101fedefa2b7e700509da41` |
| `A14_bcb955_underscore_word_frequency` | BigCodeBench/955 | 10 | matplotlib, numpy | `77002ca4d7fde4bd9f7c1b3480443e581e2eb46ee96e77b95b97657ef3859694` |

The sha256 is over the canonical JSON of the eight source fields the derivation consumes
(`task_id`, `complete_prompt`, `instruct_prompt`, `canonical_solution`, `code_prompt`, `test`,
`entry_point`, `libs`), so it pins the exact record, not just the dataset.

## How many, and why ten

Every task costs **15 configs × 3 reps = 45 units**. Round-1 measured cost, from the 180 A units
on disk: mean 242.9 s/unit, median 104.2 s, p90 901 s (the 900 s cap). So one *round-1-difficulty*
A task ≈ 3.0 h of wall clock. These tasks are harder by construction, so more attempts will run to
the cap; at a plausible ~450 s mean the cost is ≈ **5.6 h per task**.

- **10 tasks ≈ 56 h** on that estimate (28–31 h if they behave like round-1 A tasks; 112 h if
  every attempt hits the 900 s cap). Round 1 in total was 20 h across three nights, so this is a
  real multi-night addition and is the binding constraint on the number.
- **Why not 8:** selection here is *structural, not measured* (next section). Some of these ten
  will land saturated or unpassable, and that cannot be known in advance. Ten leaves 7–8 useful
  tasks after 2–3 duds; eight leaves 5–6.
- **Why not 12:** ~67–82 h, and `A_coding` would become 16 tasks against 8 for B+C+D combined —
  A's 0.35 weight would then be ~75% derived third-party content. Ten already makes it 14 tasks,
  of which 10 are derived; that is the ceiling worth accepting for one round.

## Selection criterion

Applied to all 148 hard tasks (`--list` prints the full survey). In order:

1. **Own ground truth must pass under this fleet's executor.** `env_health.json`'s
   `gt_check.failed_tasks` lists the **14 of 148** tasks whose canonical solution fails here —
   environment errors by construction, unpassable by any model. Excluded. `--emit` refuses to run
   if the selection ever intersects that list, so this cannot silently rot.
2. **Hermetic and deterministic.** No network, no filesystem, no subprocess, no wall-clock, no
   `unittest.mock`, and no unseeded RNG in the reference solution. Mock-heavy BigCodeBench tests
   assert on *how* a library was called, which is implementation-guessing rather than behaviour,
   and they are also the tasks most sensitive to library-version drift. This is the biggest cut.
3. **Library surface small enough for `pytest_grader.py`'s 120 s cap.** `grade.requires` is
   installed by `uv run --with` per grading run, so tensorflow / keras / torch / cv2 / gensim /
   nltk / geopandas-class dependencies are out; stdlib, numpy, pandas, scipy, matplotlib and pytz
   are in.
4. **Spec self-contained.** Everything needed to pass must be in the prompt text. A task whose
   tests assert against constants that exist only inside the reference solution is unpassable for
   the wrong reason (see `BigCodeBench/1057` below).
5. **Multi-step, as the discrimination proxy.** Preference for tasks that couple ≥2 requirements —
   compute *and* validate *and* return an exact shape — measured crudely by upstream test count
   and reference-solution length. Single-step tasks are exactly where round-1 A saturated.
6. **Library spread**, so the set does not collapse onto one API: 2 pure-stdlib, 1 pandas+json+re,
   2 numpy/pandas, 1 datetime/pytz, 1 scikit-learn, 3 matplotlib. Upstream BigCodeBench-Hard is
   itself matplotlib-heavy, so 4/10 touching matplotlib is representative rather than skewed.

### The funnel, in numbers

| Stage | Remaining |
|---|---|
| BigCodeBench-Hard `v0.1.4` | 148 |
| after 1 — own ground truth passes here | 134 |
| after 2 — hermetic and deterministic | 43 |
| after 3 — light library surface | 26 |

The 26-task pool that criteria 4–6 then chose from:
`120, 139, 162, 199, 239, 267, 302, 341, 367, 399, 458, 513, 530, 532, 560, 567, 618, 854, 870,
915, 916, 928, 955, 1057, 1077, 1085`.

**One deliberate exception:** `BigCodeBench/969` is not in that pool — scikit-learn is excluded by
criterion 3's blanket rule — and was admitted anyway, so the set is not blind to the single most
common heavyweight library in real data work. Cost measured, not assumed: its graded run is 1.3 s
warm and 31 s on a cold `uv` cache, both inside the 120 s cap. It was chosen over the other
sklearn candidate (`752`) because it is the cheaper import for the same validation-heavy shape.

### This criterion is weaker than measuring, and here is exactly how

Criterion 5 is a **structural guess at difficulty, not a measurement.** The external lane has not
produced per-task results across the fleet yet — the only per-task data on disk is
`bcb__opus__q4.json`, one config over ten tasks (`BigCodeBench/13,15,17,19,34,37,82,89,92,93`),
none of which are in this selection. So "will some configs pass this and others fail" is an
argument from library surface and step count, not evidence.

**A post-hoc re-selection would be strictly better:** once a full 148-task lane-2 run exists per
config, rank tasks by across-config pass-rate variance and keep the ones in the discriminating
band, dropping whatever turned out to be 0/15 or 15/15. That re-selection is cheap (regenerate
`SELECTED`, re-run `--emit`) but it invalidates already-collected lane-1 units for dropped tasks.
Do it before the round-2 run, not after.

## How each task was derived (the Apache-2.0 statement of changes)

Upstream text is reused **verbatim**; the change is packaging, not content.

| File | Content |
|---|---|
| `PROMPT.md` | Upstream `instruct_prompt`, byte-for-byte — *this is exactly the lane-2 input* — inside harness framing that names the file to edit and the done-criteria. |
| `repo/src/solution.py` | Upstream `code_prompt` (its imports and signature) + `raise NotImplementedError`. |
| `grade/test_solution.py` | Upstream `test`, byte-for-byte, below a loader header. |
| `grade/ref_solution.py` | Upstream `complete_prompt` + `canonical_solution`, byte-for-byte. Never shown to the model; exists so `--verify` can prove the tests are green on truth. |
| `meta.json` | Harness metadata only, `CONTRACT.md` §1 schema, no invented fields. |

**No test was weakened, no assertion relaxed, no edge case dropped, no spec simplified.** In
particular the docstring was *not* rewritten: `instruct_prompt` is upstream's own restatement of
the same specification, and it is reproduced whole, including its trailing "You should write
self-contained code starting with:" block, because that block names the required imports and
signature and lane 2 receives it too.

Two adjustments, both to the execution environment rather than to any test:

1. **`MPLBACKEND=Agg`**, set by the loader header before the solution is imported. BigCodeBench
   forks per task and calls `plt.close('all')` in `reliability_guard`
   (`bigcodebench/eval/utils.py:326`); it never renders either. Without this a matplotlib task can
   pick the interactive macOS backend inside `pytest_grader.py`'s subprocess. No assertion depends
   on it.
2. **One shared module namespace.** Upstream concatenates the solution and the test into a single
   `__test__.py`, so the test body sees every module-level name the solution defined, not just
   `task_func`. The loader header reproduces that by copying the solution module's public globals
   into the test module's globals. Without it, any upstream test that references a prompt-level
   constant would `NameError` — an artefact of wrapping, not a real failure.

`entry_point` stays `task_func` for all ten. Renaming it to something descriptive would have read
better and broken the pairing; the pairing wins.

## Verification (2026-07-26)

`uv run eval/harness/ops/wrap_bcb_tasks.py --verify` runs both the reference solution and the
untouched stub through **unmodified** `pytest_grader.py`:

```
OK  A5_bcb854_permutation_factorials     ref  5/5  (0.01s)  | stub  1/5 assertion floor=['test_case_5']
OK  A6_bcb928_bigram_frequency_table     ref  5/5  (0.011s) | stub  0/5 assertion
OK  A7_bcb458_json_doubling_dataframe    ref  5/5  (1.943s) | stub  0/5 assertion
OK  A8_bcb870_tuple_position_means       ref  5/5  (0.278s) | stub  0/5 assertion
OK  A9_bcb513_fitness_column_stats       ref 12/12 (0.725s) | stub  2/12 assertion floor=['test_case_6','test_case_10']
OK  A10_bcb1077_timezone_mean_gap        ref  6/6  (1.805s) | stub  0/6 assertion
OK  A11_bcb969_minmax_cumsum             ref  7/7  (1.272s) | stub  0/7 assertion
OK  A12_bcb532_duplicate_histogram_norm  ref  6/6  (1.339s) | stub  0/6 assertion
OK  A13_bcb139_numeric_column_histograms ref  7/7  (0.657s) | stub  0/7 assertion
OK  A14_bcb955_underscore_word_frequency ref 10/10 (0.336s) | stub  1/10 assertion floor=['test_case_8']
```

- **10/10 reference solutions pass 100% of their tests** through the unmodified grader.
- **Nothing passes trivially:** the stub scores 0 on seven tasks and 1–2 on three.
- Slowest reference run, cold `uv` cache: 36 s (`A12`), against `pytest_grader.py`'s 120 s cap.
  Warm cache, as above, ≤2 s.

### The `assertRaises` floor — three tasks, documented, not fixed

`A5`, `A9` and `A14` each award the untouched stub 1–2 tests. Cause: upstream asserts
`assertRaises(Exception)` for the invalid-input cases, and the stub's `NotImplementedError` **is**
an `Exception`. Named explicitly in `wrap_bcb_tasks.py`'s `STUB_FLOOR` so a change that *grows*
the floor fails `--verify`.

Not fixed, deliberately, on three grounds:

- Fixing it means either editing upstream assertions (forbidden — it is the whole point that these
  are upstream's tests) or swapping the stub body to something that returns `None`, which breaks
  the `raise NotImplementedError` convention `A1`–`A4` use.
- It is a **uniform** offset (mean +0.047 on the A pass-rate across the ten tasks) that fires only
  when a model leaves the stub untouched. It shifts the level, not the ranking, and ranking is what
  A is being asked for.
- For the lane-1/lane-2 pairing it is irrelevant: lane 2 reports `pass@1` (all-or-nothing), so the
  pairing must be computed against lane 1's **all-tests-passed** indicator, not its `pass_rate`.
  2/12 is not a pass.

## Rejected candidates

| Upstream id | Why not |
|---|---|
| BigCodeBench/879 | Ground-truth failure. Listed in `env_health.json` `gt_check.failed_tasks`, and it reproduces here: the reference solution calls `np.issubdtype()` on a pandas 3 `StringDtype` column, which raises `TypeError`, so 5 of its 8 tests fail on truth. Wrapped, verified, then dropped. |
| BigCodeBench/120 | The test asserts the exact 366-date list produced by one specific `randint()` call sequence. Passing requires reproducing the reference implementation's RNG call order, not the specified behaviour. |
| BigCodeBench/1057 | Spec not self-contained: the test asserts shape `(10, 7)` for the default arguments, but the 10 animals and 7 foods exist only inside the reference solution and appear nowhere in the prompt. |
| BigCodeBench/101 | Downloads the Boston housing dataset over HTTP. |
| BigCodeBench/308 | No seed anywhere — the reference builds a 100×6 grade table from bare `random.randint`, so only the DataFrame's shape is checkable. |
| BigCodeBench/752 | Same validation-heavy shape as 969 but a much larger sklearn import cost inside the 120 s cap; 969 already covers scikit-learn. |
| the other 13 `gt_check.failed_tasks` | Unpassable under this executor (criterion 1). |
| 91 further tasks | Network / filesystem / subprocess / clock / mock / unseeded RNG (criterion 2). |
| 17 further tasks | Library too heavy to install inside the grader's 120 s cap (criterion 3). |

## Residual risks

1. **Unpinned dependencies.** `grade.requires` names distributions, not versions, so
   `pytest_grader.py` resolves whatever `uv` gives it that day. `BigCodeBench/879` is the proof
   this bites: pandas 3's `StringDtype` broke a reference solution written against pandas 2. A
   future numpy/pandas/matplotlib release can break one of these ten the same way, and it would
   surface as every config failing one task. Re-run `--verify` before each round-2 run — that is
   the whole reason it exists as a command rather than as a one-off transcript.
2. **The two lanes are not byte-identical executors.** Lane 2 runs relaxed pins in BigCodeBench's
   local executor with rlimits disabled; lane 1 runs `uv`-resolved latest inside
   `pytest_grader.py`. The upstream *assertions* are identical, the environments are not. Read the
   lane delta as directional evidence about the harness, not as a calibrated number. `env_health`'s
   0.9054 ground-truth ceiling applies to lane 2 only.
3. **Metric mismatch.** Lane 1 grades `pass_rate` (fraction of tests), lane 2 grades `pass@1`
   (all-or-nothing). Any pairing must binarise lane 1 first.
4. **Selection is unvalidated** (see above). Expect 2–3 of the ten to turn out saturated or
   unpassable.
5. **`aggregate.py` does not score these yet.** Its `ROUND1_TASKS` / `ROUND2_TASKS` sets are
   hard-coded on purpose, which is what keeps the round-1 composite byte-reproducible. Adding
   `A5`–`A14` to `ROUND2_TASKS` is a separate, deliberate edit — not done here.
