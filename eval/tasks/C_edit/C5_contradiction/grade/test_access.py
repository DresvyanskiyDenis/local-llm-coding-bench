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
    path = _REPO / "src" / "access.py"
    spec = importlib.util.spec_from_file_location("access", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


access = _load_solution()


def test_has_permission_self_inclusive():
    # comment 1: exactly the required role must be allowed
    assert access.has_permission("admin", "admin") is True
    assert access.has_permission("editor", "editor") is True


def test_has_permission_lower_rank_denied():
    assert access.has_permission("viewer", "admin") is False


def test_has_permission_higher_rank_allowed():
    assert access.has_permission("admin", "viewer") is True


def test_is_locked_out_at_threshold():
    # comment 2: exactly max_attempts must already lock out
    assert access.is_locked_out(5, max_attempts=5) is True


def test_is_locked_out_below_threshold():
    assert access.is_locked_out(4, max_attempts=5) is False


def test_is_locked_out_above_threshold():
    assert access.is_locked_out(6, max_attempts=5) is True


def test_sanitize_username_strips_and_lowers():
    # comment 3: must strip AND lowercase
    assert access.sanitize_username(" Alice ") == "alice"


def test_sanitize_username_already_clean():
    assert access.sanitize_username("bob") == "bob"


def test_round_price_to_cents_half_up_canary():
    # canary: comments 4 and 5 contradict each other over round_price_to_cents.
    # Comment 4 (switch to builtin round()) must be ignored: round(1.005, 2)
    # == 1.0 and round(2.675, 2) == 2.67 in real Python float behavior --
    # both WRONG under the documented half-up policy that comment 5 (a
    # no-op restatement of already-correct behavior) insists on.
    assert access.round_price_to_cents(1.005) == 1.01
    assert access.round_price_to_cents(2.675) == 2.68


def test_round_price_to_cents_normal_values():
    assert access.round_price_to_cents(12.345) == 12.35
    assert access.round_price_to_cents(10.0) == 10.0


def test_round_price_to_cents_rounds_down_when_below_half():
    assert access.round_price_to_cents(10.004) == 10.0


def test_round_price_to_cents_rounds_up_when_above_half():
    assert access.round_price_to_cents(10.006) == 10.01
