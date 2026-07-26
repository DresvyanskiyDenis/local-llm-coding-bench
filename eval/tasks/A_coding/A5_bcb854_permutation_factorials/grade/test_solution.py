"""Hidden tests for A5_bcb854_permutation_factorials.

DERIVED, NOT WRITTEN HERE. The test body below the marker is BigCodeBench/854 from
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

# ----- verbatim upstream test body (BigCodeBench/854) below this line -----
import unittest
class TestCases(unittest.TestCase):
    def test_case_1(self):
        result, perm = task_func([1, 2])
        expected = [3, 3]
        expected_perm = [(2, 1), (1, 2)]
        self.assertEqual(result, expected)
        self.assertCountEqual(perm, expected_perm)
    def test_case_2(self):
        result, perm = task_func([1, 2, 3])
        expected = [9, 9, 9, 9, 9, 9]
        expected_perm = [(1, 2, 3), (1, 3, 2), (2, 1, 3), (2, 3, 1), (3, 1, 2), (3, 2, 1)]
        self.assertEqual(result, expected)
        self.assertCountEqual(perm, expected_perm)
    def test_case_3(self):
        result, perm = task_func([1])
        expected = [1]
        expected_perm = [(1,)]
        self.assertEqual(result, expected)
        self.assertCountEqual(perm, expected_perm)
    def test_case_4(self):
        result, perm = task_func([])
        expected = []
        expected_perm = []
        self.assertEqual(result, expected)
        self.assertCountEqual(perm, expected_perm)
    def test_case_5(self):
        'wrong input'
        self.assertRaises(Exception, task_func, 'a')
        self.assertRaises(Exception, task_func, 1)
        self.assertRaises(Exception, task_func, {})
        self.assertRaises(Exception, task_func, -1.2)
        self.assertRaises(Exception, task_func, [1.2, 1, 4])
        self.assertRaises(Exception, task_func, [1, 'a', 4])
        self.assertRaises(Exception, task_func, [1, 2, 4, 5, 7, 9, -1])
