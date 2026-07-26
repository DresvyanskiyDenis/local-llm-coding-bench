# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Proof that every bug in B4's grade/key.json is a real defect.

One check per key id, each asserting the *correct* behaviour. A bug counts as
demonstrated only when its check FAILS against ``repo/src/importer.py`` and
PASSES against ``grade/ref_fixed/src/importer.py``.

Deterministic: the fixture CSV is written as explicit UTF-8 bytes, so the
encoding check does not depend on the machine's locale.

Usage:
    uv run eval/tasks/B_review/B4_io_encoding/grade/verify_bugs.py
Exit 0 = every key entry demonstrated.
"""

from __future__ import annotations

import importlib.util
import sys
import tempfile
from pathlib import Path

GRADE_DIR = Path(__file__).resolve().parent
BUGGY = GRADE_DIR.parent / "repo" / "src" / "importer.py"
FIXED = GRADE_DIR / "ref_fixed" / "src" / "importer.py"

CSV_TEXT = (
    "sku,name,price,quantity\n"
    "SKU-1,Müller Schräubchen,19.99,4\n"
    "SKU-2,Crème brûlée mould,7.50,2\n"
    "SKU-3,Broken row,not-a-number,1\n"
    "SKU-4,Plain widget,1.00,9\n"
    "SKU-5,Другой виджет,2.25,3\n"
)


def load_module(path: Path, name: str):
    sys.dont_write_bytecode = True  # never drop __pycache__ into the task's repo/
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def write_fixture(tmp: Path) -> Path:
    path = tmp / "export.csv"
    path.write_bytes(CSV_TEXT.encode("utf-8"))  # the vendor export is UTF-8, spec §4.1
    return path


def check_b1_encoding(mod, tmp: Path) -> None:
    """read_rows must decode the UTF-8 export without mojibake."""
    rows = mod.read_rows(write_fixture(tmp))
    names = [r["name"] for r in rows]
    assert names[0] == "Müller Schräubchen", f"row 1 name decoded as {names[0]!r}"
    assert names[1] == "Crème brûlée mould", f"row 2 name decoded as {names[1]!r}"
    assert names[4] == "Другой виджет", f"row 5 name decoded as {names[4]!r}"


def check_b2_swallowed_exception(mod, tmp: Path) -> None:
    """A row that fails to parse must be reported in errors, not dropped silently."""
    rows = mod.read_rows(write_fixture(tmp))
    errors: list[str] = []
    records = mod.parse_rows(rows, errors)
    assert len(records) == 4, f"parsed {len(records)} records, expected 4 (1 bad row)"
    assert errors, "the unparseable row was dropped without appending anything to errors"
    assert any("3" in e for e in errors), f"errors do not name the offending row: {errors}"


def check_b3_off_by_one_batches(mod, tmp: Path) -> None:
    """Every record must appear in exactly one batch."""
    records = [{"sku": f"SKU-{i}"} for i in range(7)]
    batches = mod.split_batches(records, batch_size=3)
    flat = [r for batch in batches for r in batch]
    assert flat == records, (
        f"batching dropped records: {len(flat)} of {len(records)} survived "
        f"(batch sizes {[len(b) for b in batches]})"
    )


CHECKS = [
    ("b1_wrong_encoding", check_b1_encoding),
    ("b2_swallowed_exception", check_b2_swallowed_exception),
    ("b3_off_by_one_batches", check_b3_off_by_one_batches),
]


def run(check, module, label: str):
    with tempfile.TemporaryDirectory(prefix=f"b4-{label}-") as tmp:
        try:
            check(module, Path(tmp))
        except AssertionError as exc:
            return False, str(exc)
        except Exception as exc:  # noqa: BLE001 - a crash is also "not correct"
            return False, f"{type(exc).__name__}: {exc}"
    return True, ""


def main() -> int:
    buggy = load_module(BUGGY, "b4_importer_buggy")
    fixed = load_module(FIXED, "b4_importer_fixed")

    print(f"{'bug id':<32} {'buggy':<7} {'fixed':<7} verdict")
    print("-" * 78)
    ok = True
    for bug_id, check in CHECKS:
        buggy_ok, buggy_detail = run(check, buggy, f"{bug_id}-buggy")
        fixed_ok, fixed_detail = run(check, fixed, f"{bug_id}-fixed")
        demonstrated = (not buggy_ok) and fixed_ok
        ok = ok and demonstrated
        verdict = "demonstrated" if demonstrated else "NOT DEMONSTRATED"
        print(f"{bug_id:<32} {'FAIL' if not buggy_ok else 'pass':<7} "
              f"{'PASS' if fixed_ok else 'fail':<7} {verdict}")
        if buggy_detail:
            print(f"{'':<32} buggy: {buggy_detail}")
        if not fixed_ok:
            print(f"{'':<32} fixed: {fixed_detail}")
    print()
    print("ALL BUGS DEMONSTRATED" if ok else "SOME KEY ENTRIES ARE NOT DEMONSTRATED")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
