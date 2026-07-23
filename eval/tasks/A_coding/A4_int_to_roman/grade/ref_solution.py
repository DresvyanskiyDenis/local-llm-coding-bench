"""Reference solution for A4_int_to_roman (audit only, not shipped to the model)."""

_VALUES = [
    (1000, "M"), (900, "CM"), (500, "D"), (400, "CD"),
    (100, "C"), (90, "XC"), (50, "L"), (40, "XL"),
    (10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I"),
]


def int_to_roman(num: int) -> str:
    if not isinstance(num, int) or isinstance(num, bool):
        raise ValueError("num must be an int")
    if not (1 <= num <= 3999):
        raise ValueError("num must be between 1 and 3999 inclusive")

    result = []
    remaining = num
    for value, symbol in _VALUES:
        count, remaining = divmod(remaining, value)
        result.append(symbol * count)
    return "".join(result)
