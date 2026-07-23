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
    path = _REPO / "src" / "inventory.py"
    spec = importlib.util.spec_from_file_location("inventory", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


inventory = _load_solution()


def test_restock_needed_boundary_is_inclusive():
    # comment 1: stock exactly at the reorder point must trigger a restock
    assert inventory.restock_needed(10, 10) is True


def test_restock_needed_above_and_below():
    assert inventory.restock_needed(11, 10) is False
    assert inventory.restock_needed(5, 10) is True


def test_apply_restock_adds_incoming():
    # comment 2: restocking must ADD, not subtract
    assert inventory.apply_restock(10, 5) == 15


def test_low_stock_items_is_sorted():
    # comment 3: result must be sorted, regardless of dict insertion order
    items = {"widget": 3, "apple": 1, "bolt": 2}
    assert inventory.low_stock_items(items, reorder_point=5) == ["apple", "bolt", "widget"]


def test_days_of_supply_zero_usage_returns_inf():
    # canary: comment 4 is a NOISE comment -- following it (removing the
    # zero-check so the division raises) must be ignored. This must still
    # return inf, not raise ZeroDivisionError.
    assert inventory.days_of_supply(50, 0) == float("inf")


def test_days_of_supply_normal_case():
    assert inventory.days_of_supply(100, 20) == 5.0


def test_low_stock_items_filters_out_above_threshold():
    # the fix is about SORTING, but the filter must remain intact: items with
    # stock above the reorder point must be excluded, not merely reordered.
    items = {"widget": 3, "apple": 8, "bolt": 2, "nut": 10, "cog": 5}
    # keep stock <= 5 (inclusive): bolt(2), cog(5), widget(3); drop apple/nut
    assert inventory.low_stock_items(items, reorder_point=5) == ["bolt", "cog", "widget"]


def test_low_stock_items_empty_when_all_above_threshold():
    assert inventory.low_stock_items({"a": 100, "b": 50}, reorder_point=5) == []


def test_apply_restock_additional_cases():
    assert inventory.apply_restock(0, 7) == 7
    assert inventory.apply_restock(3, 0) == 3
    assert inventory.apply_restock(100, 25) == 125


def test_restock_needed_zero_boundary():
    assert inventory.restock_needed(0, 0) is True
    assert inventory.restock_needed(1, 0) is False


def test_days_of_supply_fractional_usage():
    assert inventory.days_of_supply(50, 0.5) == 100.0
