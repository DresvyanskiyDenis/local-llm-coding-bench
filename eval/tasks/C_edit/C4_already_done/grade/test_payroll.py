import importlib.util
import os
import pathlib

_HERE = pathlib.Path(__file__).parent


def _resolve_repo():
    # Works both when the test is run in place (repo/ is a sibling of grade/)
    # and under the harness (which copies test_*.py to a temp dir and points
    # PYTHONPATH at the model's repo/).
    candidates = [_HERE / "repo", _HERE.parent / "repo"]
    candidates += [pathlib.Path(p) for p in os.environ.get("PYTHONPATH", "").split(os.pathsep) if p]
    for c in candidates:
        if (c / "src").exists():
            return c
    return _HERE.parent / "repo"


_REPO = _resolve_repo()


def _load_solution():
    path = _REPO / "src" / "payroll.py"
    spec = importlib.util.spec_from_file_location("payroll", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


payroll = _load_solution()


def test_overtime_pay_only_excess_at_premium():
    # comment 1: 45 hours @ $10/hr -> 40*10 + 5*15 = 475, NOT 45*10*1.5
    assert payroll.calculate_overtime_pay(45, 10) == 475.0


def test_overtime_pay_below_forty_no_premium():
    assert payroll.calculate_overtime_pay(35, 20) == 700.0


def test_overtime_pay_exact_forty_boundary():
    assert payroll.calculate_overtime_pay(40, 15) == 600.0


def test_overtime_pay_large_overtime():
    assert payroll.calculate_overtime_pay(50, 12) == 40 * 12 + 10 * 12 * 1.5


def test_round_to_nearest_cent_rounds_up():
    # comment 2: 10.126 must ROUND, not truncate, to 10.13
    assert payroll.round_to_nearest_cent(10.126) == 10.13


def test_round_to_nearest_cent_carries_dollar():
    assert payroll.round_to_nearest_cent(19.995) == 20.0


def test_round_to_nearest_cent_carries_up_from_fraction():
    assert payroll.round_to_nearest_cent(3.999) == 4.0


def test_round_to_nearest_cent_exact_value_unchanged():
    assert payroll.round_to_nearest_cent(5.00) == 5.0


def test_clamp_hours_negative_returns_zero():
    # canary: comment 3 is a NOISE comment (clamp_hours already does this) --
    # this must keep returning 0.0 regardless of whether the model touched
    # the guard while "fixing" a non-existent problem.
    assert payroll.clamp_hours(-8) == 0.0


def test_clamp_hours_within_range():
    assert payroll.clamp_hours(45) == 45


def test_clamp_hours_above_max():
    assert payroll.clamp_hours(75) == 60.0


def test_clamp_hours_zero_boundary():
    assert payroll.clamp_hours(0) == 0.0
