"""Validate a record dict against a small declarative schema.

`schema` maps a field name to a spec dict which may contain:
    - "type": one of "int", "float", "str", "bool" (optional — skip the
      type check if absent)
    - "required": bool (default False)
    - "min" / "max": inclusive numeric bounds (only checked for numeric
      fields that passed the type check)
    - "choices": a list of allowed values (only checked for fields that
      passed the type check)

Notes:
    - `bool` is a subclass of `int` in Python, so a field declared
      `"type": "int"` (or `"float"`) must REJECT a `True`/`False` value —
      don't let Python's `isinstance(True, int) == True` quietly pass it.
    - Fields present in `record` but absent from `schema` are ignored.
    - If a field fails its type check, do not also emit min/max/choices
      errors for it (those checks assume the value is well-typed).

Return a list of human-readable error strings, in this exact format and in
schema-iteration order (one field can contribute at most: a "required"
error, OR a "type" error, OR a "min"/"max"/"choices" error — never several
errors for the same field in the same call):
    - "field '<name>' is required"
    - "field '<name>' must be of type <type>"
    - "field '<name>' must be >= <min>"
    - "field '<name>' must be <= <max>"
    - "field '<name>' must be one of <choices>"
"""


def validate_record(record: dict, schema: dict) -> list[str]:
    raise NotImplementedError
