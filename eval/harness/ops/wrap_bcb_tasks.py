# /// script
# requires-python = ">=3.11"
# dependencies = ["pyarrow>=16"]
# ///
"""wrap_bcb_tasks.py — derive in-harness A_coding tasks from BigCodeBench-Hard.

WHY THIS EXISTS
    Round-1 A_coding is saturated (0.883-0.994 across all 15 configs) while carrying the
    largest composite weight (0.35). BigCodeBench-Hard is already vendored for the EXTERNAL
    lane (direct /v1/chat/completions, single turn, no agent). Wrapping the SAME upstream
    tasks as ordinary in-harness A tasks gives two delivery modes for one task:

        lane 1  OpenCode, tools, multiple turns   -> eval/tasks/A_coding/<derived task>
        lane 2  endpoint, single turn, no agent   -> eval/external/bigcodebench/run_bcb.py

    The lane-1 minus lane-2 difference is the harness contribution. `BCB_PAIRING.json`
    (written by this script) is what makes that pairing machine-readable.

WHAT IS AND IS NOT MODIFIED
    The vendored BigCodeBench install and the HuggingFace dataset cache are READ-ONLY here.
    Nothing upstream is touched. Per derived task, the upstream text is reused VERBATIM:
      * PROMPT.md   <- `instruct_prompt`, byte-for-byte (this is exactly the lane-2 input),
                       wrapped in harness framing that says which file to edit.
      * repo/src/solution.py <- `code_prompt` (upstream imports + signature) + a
                       `raise NotImplementedError` body. No spec text is dropped: everything
                       the docstring would have carried is in `instruct_prompt`.
      * grade/test_solution.py <- `test`, byte-for-byte, under a loader header.
      * grade/ref_solution.py  <- `complete_prompt` + `canonical_solution`, byte-for-byte.
    No test is weakened, no edge case dropped, no spec simplified.

THE ONE EXECUTION-ENVIRONMENT ADJUSTMENT
    The loader header sets `MPLBACKEND=Agg` before importing the solution. That is an
    environment knob, not a test change: BigCodeBench's own executor forks per task and
    calls plt.close('all') in reliability_guard (eval/utils.py:326), so upstream never
    renders either. Without it a matplotlib task can pick the interactive macOS backend
    inside pytest_grader's subprocess.

    It also mirrors BigCodeBench's single-namespace execution: upstream concatenates the
    solution and the test into ONE module (`__test__.py`), so the test body sees not just
    `task_func` but every module-level name the solution defined. The header reproduces
    that by copying the solution module's public globals into the test module's globals.

USAGE
    uv run eval/harness/ops/wrap_bcb_tasks.py --list           # candidate survey, writes nothing
    uv run eval/harness/ops/wrap_bcb_tasks.py --emit           # write task dirs + pairing + provenance
    uv run eval/harness/ops/wrap_bcb_tasks.py --verify         # ref solution + stub through pytest_grader
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import pyarrow as pa

HERE = Path(__file__).resolve().parent
EVAL_DIR = HERE.parent.parent                       # eval/
TASKS_DIR = EVAL_DIR / "tasks" / "A_coding"
GRADER = EVAL_DIR / "harness" / "graders" / "pytest_grader.py"
ENV_HEALTH = EVAL_DIR / "external" / "bigcodebench" / "env_health.json"

HF_CACHE = (
    Path.home() / ".cache" / "huggingface" / "datasets" / "bigcode___bigcodebench-hard"
    / "default" / "0.0.0" / "298d2cc7b96612e15e47313c3603ee124cee0c1f"
)
ARROW = HF_CACHE / "bigcodebench-hard-v0.1.4.arrow"
DATASET = "bigcode/bigcodebench-hard"
DATASET_SPLIT = "v0.1.4"
DATASET_URL = "https://huggingface.co/datasets/bigcode/bigcodebench-hard"
UPSTREAM_REPO = "https://github.com/bigcode-project/bigcodebench"
FETCH_DATE = "2026-07-25"        # when bootstrap.sh pulled the dataset (see ../PROVENANCE.md)
DERIVED_DATE = "2026-07-26"

TIMEOUT_S = 900                  # same per-attempt cap as the hand-written A tasks

# lib name (dataset `libs` field) -> pip distribution for pytest_grader's `grade.requires`.
PKG = {
    "numpy": "numpy", "pandas": "pandas", "scipy": "scipy", "matplotlib": "matplotlib",
    "seaborn": "seaborn", "sklearn": "scikit-learn", "pytz": "pytz",
    "statsmodels": "statsmodels", "dateutil": "python-dateutil", "PIL": "pillow",
    "cv2": "opencv-python-headless", "skimage": "scikit-image", "networkx": "networkx",
    "sympy": "sympy", "nltk": "nltk",
}

# The selection, in dir order. Chosen on the structural criterion documented in
# PROVENANCE.md; see --list for the full 148-task survey the shortlist came from.
SELECTED = [
    (854, "permutation_factorials"),
    (928, "bigram_frequency_table"),
    (458, "json_doubling_dataframe"),
    (870, "tuple_position_means"),
    (513, "fitness_column_stats"),
    (1077, "timezone_mean_gap"),
    (969, "minmax_cumsum"),
    (532, "duplicate_histogram_norm"),
    (139, "numeric_column_histograms"),
    (955, "underscore_word_frequency"),
]

# Considered and rejected; kept here (and in PROVENANCE.md) so the exclusions are auditable.
REJECTED = {
    879: "ground-truth failure: listed in env_health.json gt_check.failed_tasks, and it "
         "reproduces here -- the reference solution calls np.issubdtype() on a pandas 3 "
         "StringDtype column, which raises TypeError, so 5 of its 8 tests fail on truth",
    120: "test asserts the exact 366-date list produced by one specific randint() call "
         "sequence, so passing requires reproducing the reference implementation's RNG "
         "call order rather than the specified behaviour",
    1057: "spec is not self-contained: the test asserts shape (10, 7) for the default "
          "arguments, but the 10 animals and 7 foods are defined only inside the reference "
          "solution and appear nowhere in the prompt",
    752: "sklearn LinearRegression: same validation-heavy shape as 969 but a much larger "
         "import cost inside pytest_grader's 120 s cap; 969 already covers sklearn",
    101: "downloads the Boston housing dataset over HTTP",
    308: "no seed anywhere: the reference solution builds a 100x6 grade table from bare "
         "random.randint, so only the DataFrame's shape is checkable",
}


# ---------------------------------------------------------------------------
# dataset access (read-only)
# ---------------------------------------------------------------------------

def load_rows() -> list[dict]:
    if not ARROW.is_file():
        sys.exit(f"dataset arrow not found: {ARROW}\n(run the external BCB bootstrap first)")
    with pa.memory_map(str(ARROW)) as src:
        return pa.ipc.open_stream(src).read_all().to_pylist()


def gt_failed_ids() -> set[str]:
    """Tasks whose OWN ground truth fails under the vendored executor (env errors, not model
    errors). Measured by the external lane's env_health.py; 14 of 148 as of 2026-07-25. A
    derived task built on one of these can never be passed, so selection excludes them."""
    if not ENV_HEALTH.is_file():
        sys.exit(f"env_health.json not found: {ENV_HEALTH} (run the external BCB gate first)")
    return set(json.loads(ENV_HEALTH.read_text())["gt_check"]["failed_tasks"])


def record_sha256(row: dict) -> str:
    """sha256 over the fields this derivation actually consumes, canonically ordered."""
    payload = {k: row[k] for k in
               ("task_id", "complete_prompt", "instruct_prompt", "canonical_solution",
                "code_prompt", "test", "entry_point", "libs")}
    blob = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()
    return hashlib.sha256(blob).hexdigest()


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------------------
# survey (selection input)
# ---------------------------------------------------------------------------

IO_LIBS = {
    "requests", "urllib", "urllib3", "ftplib", "smtplib", "socket", "http", "subprocess",
    "psutil", "selenium", "tkinter", "turtle", "django", "flask", "cgi", "email", "imaplib",
    "poplib", "xmlrpc", "boto3", "mechanize", "bs4", "paramiko", "werkzeug", "docker",
    "wikipedia", "yfinance", "ssl", "getpass", "platform", "multiprocessing", "threading",
    "queue", "signal", "ctypes", "socketserver", "shutil", "glob", "os", "sys", "tempfile",
    "io", "pathlib", "csv", "sqlite3", "zipfile", "tarfile", "gzip", "pickle", "shelve",
    "openpyxl", "xlrd", "docx", "PyPDF2", "pypdf", "xml", "configparser", "logging",
}
HEAVY_LIBS = {
    "tensorflow", "keras", "torch", "sklearn", "cv2", "skimage", "gensim", "nltk",
    "transformers", "statsmodels", "networkx", "sympy", "numba", "Levenshtein", "folium",
    "geopandas", "shapely", "librosa", "soundfile", "wordninja", "texttable", "prettytable",
    "faker", "lxml", "chardet", "cryptography", "Crypto", "wordcloud", "geopy",
}


def survey(rows: list[dict]) -> None:
    for r in rows:
        libs = set(ast.literal_eval(r["libs"]))
        test, sol = r["test"], r["canonical_solution"]
        flags = []
        if libs & IO_LIBS:
            flags.append("IO:" + ",".join(sorted(libs & IO_LIBS)))
        if libs & HEAVY_LIBS:
            flags.append("HEAVY:" + ",".join(sorted(libs & HEAVY_LIBS)))
        if re.search(r"@patch|patch\(|MagicMock|mock_open", test):
            flags.append("MOCK")
        if re.search(r"\brandom\.|np\.random|numpy\.random", sol):
            flags.append("RAND")
        if re.search(r"datetime\.now|time\.time|datetime\.today|\.utcnow", sol + test):
            flags.append("CLOCK")
        if re.search(r"open\(|makedirs|tempfile|shutil|mkdir", sol):
            flags.append("FS")
        keep = "KEEP " if not flags else "     "
        ntests = len(re.findall(r"def (test\w+)", test))
        print(f'{keep}{r["task_id"]:20} tests={ntests:2} sol={len(sol):5} '
              f'libs={",".join(sorted(libs)):40} {" ".join(flags)}')


# ---------------------------------------------------------------------------
# emit
# ---------------------------------------------------------------------------

LOADER_HEADER = '''\
"""Hidden tests for {task_id}.

DERIVED, NOT WRITTEN HERE. The test body below the marker is {bcb_id} from
{dataset} ({split}), reproduced byte-for-byte. Do not edit it: the whole point of
this task is that lane 1 (this harness) and lane 2 (eval/external/bigcodebench) grade the
same upstream task with the same upstream assertions.

The header reproduces BigCodeBench's execution model, in which the candidate solution and
the test share ONE module namespace, so the test body sees `task_func` and every other
module-level name the solution defined.
"""

import importlib.util
import os
import pathlib

# BigCodeBench forks per task and calls plt.close('all') in reliability_guard
# (eval/utils.py:326); it never renders. Agg is the equivalent inside pytest_grader's
# subprocess. Environment only -- no assertion depends on it.
os.environ.setdefault("MPLBACKEND", "Agg")

_HERE = pathlib.Path(__file__).parent


def _resolve_repo():
    # Works both when the test is run in place (repo/ is a sibling of grade/) and under
    # the harness (which copies test_*.py to a temp dir and points PYTHONPATH at repo/).
    candidates = [_HERE / "repo", _HERE.parent / "repo"]
    candidates += [pathlib.Path(p) for p in os.environ.get("PYTHONPATH", "").split(os.pathsep) if p]
    for c in candidates:
        if (c / "src").exists():
            return c
    return _HERE.parent / "repo"


_REPO = _resolve_repo()


def _load_solution():
    path = _REPO / "src" / "solution.py"
    spec = importlib.util.spec_from_file_location("bcb_solution", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_SOLUTION = _load_solution()
globals().update({{k: v for k, v in vars(_SOLUTION).items() if not k.startswith("_")}})

# ----- verbatim upstream test body ({bcb_id}) below this line -----
'''

PROMPT_TEMPLATE = '''\
# Task: implement `task_func` in `src/solution.py`

`src/solution.py` already holds the required imports and the exact function signature.
Replace its `raise NotImplementedError` body with a working implementation. Do not rename
the function, change the signature, or drop the imports that are already there.

## Specification

{spec}

## Done when

- `src/solution.py` defines a complete, working `task_func` (no `NotImplementedError` left).
- The module-level imports and the signature are unchanged from the ones you were given.
- The implementation runs offline: no network access, no interactive prompts.
'''

STUB_BODY = '    raise NotImplementedError\n'


def title_for(row: dict, slug: str) -> str:
    first = row["instruct_prompt"].split("\n")[0]
    first = re.split(r"(?<=[a-z])\. ", first)[0].strip().rstrip(".")
    if len(first) > 88:
        first = first[:85].rstrip() + "..."
    return f"{first} (BigCodeBench-Hard {row['task_id'].split('/')[-1]})"


def requires_for(row: dict) -> list[str]:
    """Third-party packages the graded run needs: solution libs + the test's own imports."""
    names = set(ast.literal_eval(row["libs"]))
    for m in re.finditer(r"(?m)^\s*(?:import|from)\s+([A-Za-z_][\w.]*)", row["test"]):
        names.add(m.group(1).split(".")[0])
    out = set()
    for n in sorted(names):
        if n in sys.stdlib_module_names or n in {"unittest", "pytest"}:
            continue
        if n not in PKG:
            sys.exit(f"{row['task_id']}: no pip mapping for lib {n!r} -- add it to PKG")
        out.add(PKG[n])
    return sorted(out)


def dir_name(bcb_num: int, slug: str, index: int) -> str:
    return f"A{index}_bcb{bcb_num}_{slug}"


def emit(rows_by_id: dict[str, dict]) -> list[dict]:
    gt_failed = gt_failed_ids()
    clash = [f"BigCodeBench/{n}" for n, _ in SELECTED if f"BigCodeBench/{n}" in gt_failed]
    if clash:
        sys.exit(f"selection includes ground-truth-failing tasks, refusing to emit: {clash}")

    pairing = []
    for offset, (bcb_num, slug) in enumerate(SELECTED):
        bcb_id = f"BigCodeBench/{bcb_num}"
        row = rows_by_id[bcb_id]
        index = 5 + offset                       # A1..A4 are the hand-written round-1 tasks
        task_id = dir_name(bcb_num, slug, index)
        tdir = TASKS_DIR / task_id
        (tdir / "repo" / "src").mkdir(parents=True, exist_ok=True)
        (tdir / "grade").mkdir(parents=True, exist_ok=True)

        stub = row["code_prompt"].rstrip("\n") + "\n" + STUB_BODY
        (tdir / "repo" / "src" / "solution.py").write_text(stub)

        prompt = PROMPT_TEMPLATE.format(spec=row["instruct_prompt"].strip())
        (tdir / "PROMPT.md").write_text(prompt)

        header = LOADER_HEADER.format(task_id=task_id, bcb_id=bcb_id,
                                      dataset=DATASET, split=DATASET_SPLIT)
        (tdir / "grade" / "test_solution.py").write_text(header + row["test"].rstrip("\n") + "\n")

        ref = (f'# Reference solution for {task_id}: {bcb_id} `complete_prompt` +\n'
               f'# `canonical_solution` from {DATASET} ({DATASET_SPLIT}), verbatim. Not shown\n'
               f'# to the model; used by --verify to prove the tests are green on truth.\n'
               + row["complete_prompt"].rstrip("\n") + "\n"
               + row["canonical_solution"].rstrip("\n") + "\n")
        (tdir / "grade" / "ref_solution.py").write_text(ref)

        requires = requires_for(row)
        est_ctx = round((len(prompt) + len(stub)) / 4 / 100) * 100
        meta = {
            "id": task_id,
            "suite": "A_coding",
            "title": title_for(row, slug),
            "grader": "pytest",
            "timeout_s": TIMEOUT_S,
            "est_ctx_tokens": est_ctx,
            "entrypoint": "src/solution.py",
            "grade": {"test_file": "grade/test_solution.py", "requires": requires},
        }
        (tdir / "meta.json").write_text(json.dumps(meta, indent=2) + "\n")

        pairing.append({
            "harness_task": f"A_coding/{task_id}",
            "bigcodebench_task_id": bcb_id,
            "entry_point": row["entry_point"],
            "libs": ast.literal_eval(row["libs"]),
            "requires": requires,
            "n_upstream_tests": len(re.findall(r"def (test\w+)", row["test"])),
            "source_record_sha256": record_sha256(row),
        })
        print(f"emitted {task_id:44} <- {bcb_id:20} requires={requires}")
    return pairing


PAIRING_DOC = {
    "what": (
        "Lane pairing for the BigCodeBench-derived A_coding tasks. Each entry is ONE upstream "
        "task delivered two ways: lane 1 = through OpenCode with tools and multiple turns "
        "(eval/tasks/A_coding/<harness_task>, graded by pytest_grader.py); lane 2 = straight at "
        "/v1/chat/completions, single turn, no agent (eval/external/bigcodebench/run_bcb.py, "
        "graded by BigCodeBench itself). Lane 1 minus lane 2, on the same task and the same "
        "assertions, is the harness contribution."
    ),
    "lane2_note": (
        "Lane 2 must actually cover these ids for a pair to exist. run_bcb.py --limit N maps to "
        "--id-range 0-N over the 148-task hard split, so a truncated lane-2 run may not include "
        "every id below; pair only on ids present in the lane-2 eval_results.json."
    ),
    "comparability": (
        "Lane 2's absolute pass@1 is a within-fleet number (relaxed pins, local executor). Lane 1 "
        "runs the same upstream assertions but under uv-resolved latest deps inside pytest_grader, "
        "so the two executors are NOT byte-identical either. Read the difference as directional "
        "evidence about the harness, not as a calibrated delta."
    ),
}


def write_pairing(pairing: list[dict]) -> None:
    doc = dict(PAIRING_DOC)
    doc.update({
        "dataset": DATASET,
        "dataset_split": DATASET_SPLIT,
        "derived_on": DERIVED_DATE,
        "n_pairs": len(pairing),
        "pairs": pairing,
    })
    (TASKS_DIR / "BCB_PAIRING.json").write_text(json.dumps(doc, indent=2) + "\n")
    print(f"wrote {TASKS_DIR / 'BCB_PAIRING.json'}")


# ---------------------------------------------------------------------------
# verify
# ---------------------------------------------------------------------------

def run_grader(task_dir: Path, solution_src: str) -> dict:
    with tempfile.TemporaryDirectory(prefix="bcb_verify_") as tmp:
        run = Path(tmp)
        (run / "repo" / "src").mkdir(parents=True)
        (run / "repo" / "src" / "solution.py").write_text(solution_src)
        out = run / "verdict.json"
        proc = subprocess.run(
            ["uv", "run", str(GRADER), "--task", str(task_dir), "--run", str(run),
             "--out", str(out)],
            capture_output=True, text=True,
        )
        if proc.returncode != 0:
            return {"grader_error": proc.stderr[-1500:]}
        return json.loads(out.read_text())


# Tests the untouched stub passes anyway, because upstream asserts `assertRaises(Exception)`
# and the stub's `raise NotImplementedError` satisfies that (NotImplementedError IS an
# Exception). NOT a defect introduced here and NOT worked around by editing upstream tests:
# it is a documented floor. Named so that a future change that GROWS the floor is caught.
STUB_FLOOR = {
    854: (1, ["test_case_5"]),
    513: (2, ["test_case_6", "test_case_10"]),
    955: (1, ["test_case_8"]),
}


def verify() -> int:
    bad = 0
    for offset, (bcb_num, slug) in enumerate(SELECTED):
        task_id = dir_name(bcb_num, slug, 5 + offset)
        tdir = TASKS_DIR / task_id
        ref = (tdir / "grade" / "ref_solution.py").read_text()
        stub = (tdir / "repo" / "src" / "solution.py").read_text()

        rv = run_grader(tdir, ref)
        sv = run_grader(tdir, stub)
        expected_floor = STUB_FLOOR.get(bcb_num, (0, []))[0]
        ref_ok = rv.get("total", 0) > 0 and rv.get("passed") == rv.get("total")
        stub_ok = sv.get("passed", -1) == expected_floor and sv.get("passed") < sv.get("total", 0)
        ok = ref_ok and stub_ok
        bad += 0 if ok else 1
        note = "" if expected_floor == 0 else f' floor={STUB_FLOOR[bcb_num][1]}'
        print(f'{"OK  " if ok else "BAD "}{task_id:44} ref {rv.get("passed")}/{rv.get("total")} '
              f'({rv.get("duration_s")}s) | stub {sv.get("passed")}/{sv.get("total")} '
              f'{sv.get("failure_class")}{note} | '
              f'{rv.get("detail", rv.get("grader_error", ""))[:70]}')
    print(f"\n{len(SELECTED) - bad}/{len(SELECTED)} tasks green on truth, and dead on the stub "
          f"up to the documented assertRaises floor")
    return 1 if bad else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--list", action="store_true", help="survey all 148 hard tasks, write nothing")
    ap.add_argument("--emit", action="store_true", help="write the task dirs + BCB_PAIRING.json")
    ap.add_argument("--verify", action="store_true", help="ref solution + stub through pytest_grader")
    args = ap.parse_args()

    if args.list:
        survey(load_rows())
        return 0
    if args.emit:
        rows = {r["task_id"]: r for r in load_rows()}
        write_pairing(emit(rows))
        print(f"\narrow sha256 {file_sha256(ARROW)}  {ARROW.name}")
        return 0
    if args.verify:
        return verify()
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
