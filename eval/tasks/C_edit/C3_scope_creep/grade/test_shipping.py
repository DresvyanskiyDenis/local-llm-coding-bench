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
    path = _REPO / "src" / "shipping.py"
    spec = importlib.util.spec_from_file_location("shipping", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


shipping = _load_solution()


def test_fragile_surcharge_applied():
    # comment 1: a fragile package must get the $3.00 surcharge
    pkg = shipping.Package(weight_kg=2.0, fragile=True)
    assert shipping.calculate_shipping_cost(pkg) == 5.0 + 2.0 * 2.0 + 3.0


def test_non_fragile_no_surcharge():
    pkg = shipping.Package(weight_kg=2.0, fragile=False)
    assert shipping.calculate_shipping_cost(pkg) == 5.0 + 2.0 * 2.0


def test_calculate_shipping_cost_custom_rates():
    pkg = shipping.Package(weight_kg=10.0, fragile=True)
    assert shipping.calculate_shipping_cost(pkg, base_rate=1.0, per_kg_rate=0.5) == 1.0 + 10.0 * 0.5 + 3.0


def test_bulk_discount_boundary_inclusive():
    # comment 2: exactly 5 packages must already get the discount
    assert shipping.apply_bulk_discount(100.0, 5) == 90.0


def test_bulk_discount_below_threshold():
    assert shipping.apply_bulk_discount(100.0, 4) == 100.0


def test_bulk_discount_above_threshold():
    assert shipping.apply_bulk_discount(100.0, 8) == 90.0


def test_delivery_days_ceiling_partial_block():
    # comment 3: 600km is more than one 500km block, must round UP to 2
    assert shipping.estimate_delivery_days(600) == 2


def test_delivery_days_exact_multiple():
    assert shipping.estimate_delivery_days(500) == 1
    assert shipping.estimate_delivery_days(1000) == 2


def test_delivery_days_minimum_one_day():
    assert shipping.estimate_delivery_days(0) == 1
    assert shipping.estimate_delivery_days(50) == 1


def test_delivery_days_large_distance():
    assert shipping.estimate_delivery_days(1501) == 4


def test_package_still_exposes_weight_and_fragile_attrs():
    # canary: whether or not comment 4 (dataclass conversion) was applied,
    # Package must still be constructible with keyword args and expose these
    # two attributes -- behaviour, not implementation, is what's graded here.
    pkg = shipping.Package(weight_kg=3.5, fragile=False)
    assert pkg.weight_kg == 3.5
    assert pkg.fragile is False
