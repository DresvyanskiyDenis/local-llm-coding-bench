import importlib.util
import os
import pathlib

import pytest

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
    path = _REPO / "src" / "solution.py"
    spec = importlib.util.spec_from_file_location("solution", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


solution = _load_solution()

CASES = [
    (1, "I"),
    (3, "III"),
    (4, "IV"),
    (5, "V"),
    (9, "IX"),
    (10, "X"),
    (40, "XL"),
    (49, "XLIX"),
    (50, "L"),
    (90, "XC"),
    (99, "XCIX"),
    (100, "C"),
    (400, "CD"),
    (444, "CDXLIV"),
    (500, "D"),
    (900, "CM"),
    (944, "CMXLIV"),
    (999, "CMXCIX"),
    (1000, "M"),
    (1994, "MCMXCIV"),
    (2026, "MMXXVI"),
    (3999, "MMMCMXCIX"),
]


@pytest.mark.parametrize("num,expected", CASES)
def test_known_values(num, expected):
    assert solution.int_to_roman(num) == expected


@pytest.mark.parametrize("bad", [0, -1, 4000, 10000])
def test_out_of_range_raises(bad):
    with pytest.raises(ValueError):
        solution.int_to_roman(bad)


@pytest.mark.parametrize("bad", [True, False, "10", 3.5, None])
def test_wrong_type_raises(bad):
    with pytest.raises(ValueError):
        solution.int_to_roman(bad)


def _roman_oracle(n: int) -> str:
    """Independent canonical greedy encoder used as a test oracle.

    Written separately from the reference solution; the subtractive greedy
    encoding is the unique canonical Roman numeral for every n in [1, 3999],
    so a solution that matches this for ALL 3999 values cannot be a
    hardcoded lookup of the visible CASES or a wrong-but-close formula.
    """
    table = [
        (1000, "M"), (900, "CM"), (500, "D"), (400, "CD"),
        (100, "C"), (90, "XC"), (50, "L"), (40, "XL"),
        (10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I"),
    ]
    out = []
    for value, symbol in table:
        while n >= value:
            out.append(symbol)
            n -= value
    return "".join(out)


def test_exhaustive_against_independent_oracle():
    for n in range(1, 4000):
        assert solution.int_to_roman(n) == _roman_oracle(n), n


EXTRA_CASES = [
    (8, "VIII"),
    (14, "XIV"),
    (19, "XIX"),
    (200, "CC"),
    (246, "CCXLVI"),
    (789, "DCCLXXXIX"),
    (2000, "MM"),
    (3000, "MMM"),
    (1666, "MDCLXVI"),
    (2444, "MMCDXLIV"),
    (3549, "MMMDXLIX"),
    (3888, "MMMDCCCLXXXVIII"),  # longest numeral: every symbol group maxed out
]


@pytest.mark.parametrize("num,expected", EXTRA_CASES)
def test_extra_boundary_values(num, expected):
    assert solution.int_to_roman(num) == expected


def test_output_is_uppercase_and_valid_charset():
    for n in (1, 4, 44, 946, 3888, 3999):
        r = solution.int_to_roman(n)
        assert r == r.upper()
        assert set(r) <= set("IVXLCDM")
