# Provenance — IFEval (google-research `instruction_following_eval`)

Vendored **unmodified** on **2026-07-25**. Any local change to these files forfeits the
"grader nobody in this project wrote" property that is the entire point of round 2 —
do not edit them. Adapter-side glue lives in `../run_ifeval.py`.

- **Upstream:** <https://github.com/google-research/google-research/tree/master/instruction_following_eval>
- **Raw base URL:** `https://raw.githubusercontent.com/google-research/google-research/master/instruction_following_eval/`
- **Paper:** Zhou et al., *Instruction-Following Evaluation for Large Language Models*,
  [arXiv:2311.07911](https://arxiv.org/abs/2311.07911)
- **License:** Apache-2.0 (`LICENSE`, repository root)
- **Fetched:** 2026-07-25 (branch `master`, no tag/pin upstream — sha256 below is the pin)

## Files and sha256

| File | sha256 |
|---|---|
| `instruction_following_eval/instructions.py` | `60e086f5342a03ce8e18b64bbcccf86308f523c08aa826707a562150a52f3edf` |
| `instruction_following_eval/instructions_registry.py` | `ec92d72c264f6d906978613085db262356174300370a3fffe6fefd5969ce9cfc` |
| `instruction_following_eval/instructions_util.py` | `a73797261eee5bf447e279d82a2b700b1bdd3cb1193412dbab1270a85832bc6b` |
| `instruction_following_eval/evaluation_lib.py` | `35decc06000718487f44d7deafa6d3f48a8ec0886281edf40162c0265b7d248c` |
| `instruction_following_eval/evaluation_main.py` | `e6df07a04d25a0e7134933ba2400c26e0129a243e449c88df55043e583fc4b4a` |
| `LICENSE` | `cfc7749b96f63bd31c3c42b5c471bf756814053e847c10f3eb003417bc523d30` |
| `README.md` | `fef3c44408e4b39837af345095ccce7da798853fd60ea94a1de63afa9d3d67b3` |
| `../data/input_data.jsonl` (541 prompts) | `67ffeee0fcb87c317c5b08a2de85557b4a7e96ada6178aa645b4954fe4b53d49` |

Verify with:

```bash
cd eval/external/ifeval
shasum -a 256 vendor/instruction_following_eval/*.py vendor/LICENSE vendor/README.md data/input_data.jsonl
```

## Two notes on layout

1. **The scoring functions moved upstream.** `IMPLEMENTATION_PLAN.md` §5 says to import
   `test_instruction_following_strict` / `_loose` from `evaluation_main.py`. Upstream has since
   split them into `evaluation_lib.py`; `evaluation_main.py` is now only an absl CLI wrapper.
   Both files are vendored; `run_ifeval.py` imports from `evaluation_lib`. The functions
   themselves are unchanged and still theirs.
2. **The directory nesting is load-bearing.** The vendored modules import each other as
   `from instruction_following_eval import instructions`, so they only resolve if their
   parent directory is on `sys.path` and they sit inside a directory of that name. Python 3
   implicit namespace packages make this work with no `__init__.py` (upstream has none
   either). `run_ifeval.py` therefore does `sys.path.insert(0, <.../vendor>)`.

## Runtime dependencies (installed by `uv run`, not vendored)

`absl-py`, `langdetect`, `nltk`, `immutabledict`.

`instructions_util.py:135` calls `nltk.data.load("nltk:tokenizers/punkt/english.pickle")`.
The `punkt` corpus is pre-downloaded into the repo-local `../nltk_data/` (gitignored, recreated
by `../bootstrap_nltk.py`) and `run_ifeval.py` sets `NLTK_DATA` to it, so a scoring run never
blocks on a network fetch mid-eval.
