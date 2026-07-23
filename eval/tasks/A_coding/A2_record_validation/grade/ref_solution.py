"""Reference solution for A2_record_validation (audit only, not shipped to the model)."""

_TYPE_MAP = {"int": int, "float": (int, float), "str": str, "bool": bool}


def validate_record(record: dict, schema: dict) -> list[str]:
    errors: list[str] = []
    for field, spec in schema.items():
        if field not in record:
            if spec.get("required", False):
                errors.append(f"field '{field}' is required")
            continue

        value = record[field]
        expected_type = spec.get("type")
        if expected_type is not None:
            py_type = _TYPE_MAP[expected_type]
            is_bool_leak = expected_type in ("int", "float") and isinstance(value, bool)
            if is_bool_leak or not isinstance(value, py_type):
                errors.append(f"field '{field}' must be of type {expected_type}")
                continue

        is_numeric = isinstance(value, (int, float)) and not isinstance(value, bool)

        if "min" in spec and is_numeric and value < spec["min"]:
            errors.append(f"field '{field}' must be >= {spec['min']}")
            continue
        if "max" in spec and is_numeric and value > spec["max"]:
            errors.append(f"field '{field}' must be <= {spec['max']}")
            continue
        if "choices" in spec and value not in spec["choices"]:
            errors.append(f"field '{field}' must be one of {spec['choices']}")
            continue

    return errors
