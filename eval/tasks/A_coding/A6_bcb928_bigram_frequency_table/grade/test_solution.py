"""Hidden tests for A6_bcb928_bigram_frequency_table.

DERIVED, NOT WRITTEN HERE. The test body below the marker is BigCodeBench/928 from
bigcode/bigcodebench-hard (v0.1.4), reproduced byte-for-byte. Do not edit it: the whole point of
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
globals().update({k: v for k, v in vars(_SOLUTION).items() if not k.startswith("_")})

# ----- verbatim upstream test body (BigCodeBench/928) below this line -----
import unittest
class TestCases(unittest.TestCase):
    def test_case_1(self):
        result = task_func('abcdef')
        self.assertEqual(result['ab'], 1)
        self.assertEqual(result['ac'], 0)
        self.assertEqual(result['bc'], 1)
        self.assertEqual(result['cb'], 0)
        self.assertEqual(result['zz'], 0)
        
    def test_case_2(self):
        result = task_func('aabbcc')
        self.assertEqual(result['aa'], 1)
        self.assertEqual(result['ab'], 1)
        self.assertEqual(result['ba'], 0)
        self.assertEqual(result['bb'], 1)
        self.assertEqual(result['bc'], 1)
        
    def test_case_3(self):
        result = task_func('fedcba')
        self.assertEqual(result['fe'], 1)
        self.assertEqual(result['ef'], 0)
        self.assertEqual(result['dc'], 1)
        self.assertEqual(result['ba'], 1)
        self.assertEqual(result['zz'], 0)
    def test_case_4(self):
        result = task_func('cadbfe')
        self.assertEqual(result['ca'], 1)
        self.assertEqual(result['ad'], 1)
        self.assertEqual(result['db'], 1)
        self.assertEqual(result['fe'], 1)
        self.assertEqual(result['zz'], 0)
    def test_case_5(self):
        result = task_func('')
        self.assertEqual(result['ab'], 0)
        self.assertEqual(result['zz'], 0)
