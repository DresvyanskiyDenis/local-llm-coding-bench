# Provenance — BigCodeBench

Third-party code used **unmodified**. Nothing under `.venv/` or in the installed
`bigcodebench` package has been patched; every deviation from upstream defaults is expressed
either as a **CLI flag** in `run_bcb.py` / `env_health.py` or by the **interposed proxy** that
generation is pointed at (last row of the deviations table — it is the largest deviation and it
is not something the client could have been flagged into), and recorded in the result JSON.

## Source

| Item | Value |
|---|---|
| Package | `bigcodebench` |
| Version | **0.2.5** |
| PyPI JSON | <https://pypi.org/pypi/bigcodebench/0.2.5/json> |
| sdist | <https://files.pythonhosted.org/packages/source/b/bigcodebench/bigcodebench-0.2.5.tar.gz> |
| sdist sha256 | `1e3897b1f2052dfe25100cc242f905ce526f35b93822a06f8cd4d85a9454410b` |
| wheel | `bigcodebench-0.2.5-py3-none-any.whl` |
| wheel sha256 | `7adda739687317102db71b3088d2b6e8350c887a16245a7e7c5272f893c11ae3` |
| Upstream upload | 2025-03-31 |
| Installed | **2026-07-25** |
| Upstream repo | <https://github.com/bigcode-project/bigcodebench> |
| Dataset | `bigcode/bigcodebench-hard`, split `v0.1.4` (148 tasks), fetched by the package itself |
| Local env | CPython 3.12.13, Darwin arm64, `uv` 0.11.31 |

`requirements-eval-0.2.5.txt` in this directory is a **byte-identical copy** of
`Requirements/requirements-eval.txt` from that sdist, kept so the pin-relaxation is auditable
without re-downloading:

    sha256  a4d01fb12cbce5223b51f982265cb7975bea770b758cd85cc91b803d3293e39f

(Verified identical to `main` at fetch time.)

## Install strategy

`bootstrap.sh`, re-runnable, three stages:

**1. `uv pip install --no-deps bigcodebench==0.2.5`.** The package declares `vllm` as a hard
dependency and `vllm` has no arm64/macOS wheel. `--no-deps` is safe because `vllm` is imported
**lazily**, inside `provider/__init__.py::make_model`, only on the `backend == "vllm"` branch —
verified in the *installed* package, and asserted by `bootstrap.sh` itself, which imports
`bigcodebench.generate` and `bigcodebench.evaluate` and then checks `"vllm" not in sys.modules`.

**2. The curated runtime set** (installed *with* their own dependencies):

```
openai datasets transformers tqdm termcolor numpy rich appdirs fire multipledispatch
pqdm tempdir tree_sitter tree-sitter-python wget gradio-client e2b httpx
```

`gradio-client` and `e2b` are required even though only the local executor is used:
`evaluate.py` imports both at module top level (lines 15–16).

**3. `requirements-eval.txt` with every pin stripped.** Bulk resolution fails (upstream pins are
mutually inconsistent once relaxed), so `bootstrap.sh` falls back to per-package installs and
records every failure in `install_report.json`.

## Relaxed pins — result

- **71** distinct packages in `requirements-eval.txt` (73 lines; `requests`, `statsmodels` and
  `xlrd` appear twice).
- **70 / 71 installed**, **62 pins relaxed**.
- **1 package could not be installed at all:** `python-Levenshtein-wheels` — abandoned upstream,
  no wheel or sdist for CPython 3.12. Harmless here: the `Levenshtein` module it used to provide
  is supplied by `Levenshtein` (from the `Levenshtein==0.25.0` line, relaxed), which **is**
  installed, so `import Levenshtein` resolves.

The pins that motivated the decision, and where they actually landed:

| Package | Pinned | Resolved |
|---|---|---|
| numpy | 1.21.2 | 2.4.6 |
| numba | 0.55.0 | 0.66.0 |
| keras | 2.11.0 | 3.15.0 |
| tensorflow | 2.11.0 | 2.21.0 |
| gensim | 4.3.2 | 4.4.0 |
| scipy | 1.7.2 | 1.18.0 |
| pandas | 2.0.3 | 3.0.5 |
| scikit-learn | 1.3.1 | 1.9.0 |
| scikit-image | 0.18.0 | 0.26.0 |
| matplotlib | 3.7.0 | 3.11.1 |
| networkx | 2.6.3 | 3.6.1 |
| opencv-python-headless | 4.9.0.80 | 5.0.0.93 |
| Django | 4.2.7 | 6.0.7 |
| nltk | 3.8 | 3.10.0 |
| Pillow | 10.3.0 | 12.3.0 |

The full 62-entry mapping, machine-readable, is in **`install_report.json`**
(`pins_relaxed`), regenerated on every `bootstrap.sh` run.

## Deviations from upstream defaults (flags and the proxy, no code edits)

| Flag | Upstream default | Used here | Why |
|---|---|---|---|
| `--execution` | `gradio` | `local` | Gradio uploads solutions to a third-party HF Space; Docker was rejected on RAM grounds (§1, §10.1 of the implementation plan). |
| `--max-as-limit` / `--max-data-limit` / `--max-stack-limit` | `30720` / `30720` / `10` | `0` / `0` / `0` | **Required on macOS.** `resource.setrlimit(RLIMIT_AS\|RLIMIT_DATA, v)` raises `ValueError: current limit exceeds maximum limit` for *every* value tried (64 MB → 30 GB) on Darwin arm64 / CPython 3.12.13. `reliability_guard` (`eval/utils.py:301`) applies both unconditionally, so with the defaults every task fails **before its test body runs** — a first ground-truth run logged 80 such errors in ~90 tasks. The guard is gated on `if max_as_limit and max_data_limit and max_stack_limit:`, so `0` skips only the rlimit block; TZ pinning, `faulthandler` disabling and the builtins hardening remain. Cost: executed solutions have no memory ceiling, hence `--parallel 4`. |
| `--max-new-tokens` | `1280` | `4096` | Thinking models exhaust 1280 mid-solution and the sanitizer then sees a truncated program. |
| `--bs` | `None` | `1` | With `None`, `generate.py` writes nothing to disk until the whole split finishes (`generate.py:88`), so `--resume` has nothing to resume from after a crash. |
| `--parallel` | `cpu_count() // 2` | `4` | With rlimits off, and while a 35B GGUF may be resident, unbounded workers are a memory risk. |
| `--pass-k` | `"1,5,10"` | *not passed* | `fire` would coerce `1` to an int and `evaluate.py:218` then iterates it. The default already yields only `pass@1` when `n_samples == 1`. |
| `--base-url` | the served model, directly | `http://127.0.0.1:8899/v1` — `eval/harness/eval_proxy.py`, in front of the served model | **The largest deviation, and the one no flag on the upstream client could express.** `run_bcb.py` hands `run_generate` the *proxy* URL, never `:8888` (`run_bcb.py:1052-1053`), so generation never reaches the served model directly. The proxy rewrites both directions. **Request:** on every `POST …/chat/completions` it forces `NEUTRAL_SAMPLING` — temperature 0 · top_p 1 · top_k 0 · min_p 0 · presence_penalty 0 · frequency_penalty 0 (`eval_proxy.py:64-71`) — over BigCodeBench's hardcoded `top_p = 0.95` (`gen/util/openai_request.py:17`) and over the per-model server defaults the client cannot reach at all. **Response:** it strips reasoning out of every choice's `message.content`, four observed shapes — `<think>…</think>`, orphan `</think>`, unclosed `<think>`, harmony `<\|channel\|>analysis` (`eval_proxy.py:81-87`) — because this fleet leaks the monologue into `content` with no `reasoning_content` field. Both halves are recorded per config: `generation.sampling_injected` + `generation.proxy_stats` for the request rewrite, `generation.reasoning_stripped` for the response rewrite, and `generation.completions_provenance` for whether the scored completions went through it at all. |

## Consequence for the numbers

Relaxed pins + local execution ⇒ **BigCodeBench-Hard `pass@1` from this repo is a WITHIN-FLEET
number.** Every config runs under the identical executor, so the *ranking* — which is what the
Spearman correlation in Phase 6 consumes — is unaffected. The *absolute* value is **not
comparable to the public BigCodeBench leaderboard** and must never be quoted as if it were.
Each result JSON carries this in its `comparability` field, and `env_health.json` carries the
measured ground-truth pass rate, which is the hard ceiling on any model's score here.
