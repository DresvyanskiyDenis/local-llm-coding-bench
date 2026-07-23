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
    path = _REPO / "src" / "solution.py"
    spec = importlib.util.spec_from_file_location("solution", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


solution = _load_solution()

SCHEMA = {
    "name": {"type": "str", "required": True},
    "age": {"type": "int", "required": True, "min": 0, "max": 130},
    "country": {"type": "str", "choices": ["DE", "US", "FR"]},
    "score": {"type": "float", "min": 0.0, "max": 1.0},
}


def test_valid_record_has_no_errors():
    record = {"name": "Denis", "age": 34, "country": "DE", "score": 0.9}
    assert solution.validate_record(record, SCHEMA) == []


def test_missing_required_field():
    record = {"age": 34}
    errors = solution.validate_record(record, SCHEMA)
    assert "field 'name' is required" in errors


def test_optional_field_missing_is_not_an_error():
    record = {"name": "Denis", "age": 34}
    errors = solution.validate_record(record, SCHEMA)
    assert errors == []


def test_wrong_type():
    record = {"name": "Denis", "age": "thirty"}
    errors = solution.validate_record(record, SCHEMA)
    assert "field 'age' must be of type int" in errors


def test_bool_rejected_for_int_field():
    # isinstance(True, int) is True in Python -- must be explicitly rejected
    record = {"name": "Denis", "age": True}
    errors = solution.validate_record(record, SCHEMA)
    assert "field 'age' must be of type int" in errors


def test_min_bound_violation():
    record = {"name": "Denis", "age": -1}
    errors = solution.validate_record(record, SCHEMA)
    assert "field 'age' must be >= 0" in errors


def test_max_bound_violation():
    record = {"name": "Denis", "age": 200}
    errors = solution.validate_record(record, SCHEMA)
    assert "field 'age' must be <= 130" in errors


def test_bounds_are_inclusive():
    record = {"name": "Denis", "age": 0}
    assert solution.validate_record(record, SCHEMA) == []
    record = {"name": "Denis", "age": 130}
    assert solution.validate_record(record, SCHEMA) == []


def test_choices_violation():
    record = {"name": "Denis", "age": 34, "country": "RU"}
    errors = solution.validate_record(record, SCHEMA)
    assert "field 'country' must be one of ['DE', 'US', 'FR']" in errors


def test_type_error_suppresses_bound_error():
    # age fails the type check -> must NOT also emit a min/max error for age
    record = {"name": "Denis", "age": "old"}
    errors = solution.validate_record(record, SCHEMA)
    assert len(errors) == 1
    assert errors[0] == "field 'age' must be of type int"


def test_unknown_extra_fields_are_ignored():
    record = {"name": "Denis", "age": 34, "unexpected_field": "whatever"}
    assert solution.validate_record(record, SCHEMA) == []


def test_error_order_follows_schema_order():
    record = {"age": "old", "country": "RU"}
    errors = solution.validate_record(record, SCHEMA)
    assert errors == [
        "field 'name' is required",
        "field 'age' must be of type int",
        "field 'country' must be one of ['DE', 'US', 'FR']",
    ]


def test_single_min_violation_is_the_only_error():
    # age is well-typed but below min -> exactly one error, nothing else
    record = {"name": "Denis", "age": -1}
    errors = solution.validate_record(record, SCHEMA)
    assert errors == ["field 'age' must be >= 0"]


def test_float_field_max_violation():
    # the float-typed 'score' field (min 0.0, max 1.0) was previously untested
    record = {"name": "Denis", "age": 34, "score": 1.5}
    errors = solution.validate_record(record, SCHEMA)
    assert errors == ["field 'score' must be <= 1.0"]


def test_float_field_min_violation_formats_float_bound():
    record = {"name": "Denis", "age": 34, "score": -0.1}
    errors = solution.validate_record(record, SCHEMA)
    assert errors == ["field 'score' must be >= 0.0"]


def test_float_bounds_are_inclusive():
    assert solution.validate_record({"name": "D", "age": 1, "score": 0.0}, SCHEMA) == []
    assert solution.validate_record({"name": "D", "age": 1, "score": 1.0}, SCHEMA) == []


def test_bool_rejected_for_float_field():
    # bool is a subclass of int -> must also be rejected for a float field
    record = {"name": "Denis", "age": 34, "score": True}
    errors = solution.validate_record(record, SCHEMA)
    assert "field 'score' must be of type float" in errors


def test_type_error_suppresses_choices_error():
    # country fails the type check -> must NOT also emit a choices error
    record = {"name": "Denis", "age": 34, "country": 5}
    errors = solution.validate_record(record, SCHEMA)
    assert errors == ["field 'country' must be of type str"]


def test_error_order_includes_float_max_bound():
    record = {"age": "x", "score": 5.0}
    errors = solution.validate_record(record, SCHEMA)
    assert errors == [
        "field 'name' is required",
        "field 'age' must be of type int",
        "field 'score' must be <= 1.0",
    ]
