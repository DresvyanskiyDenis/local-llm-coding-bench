"""Convert an integer to a Roman numeral (classic HumanEval-style problem).

Implement `int_to_roman(num)`:
    - `num` must be an `int` in the inclusive range [1, 3999]. Any other
      type, or an int outside that range, must raise `ValueError`.
    - Return the standard subtractive-notation Roman numeral as an
      uppercase string (e.g. 4 -> "IV", 1994 -> "MCMXCIV", 3999 ->
      "MMMCMXCIX").
"""


def int_to_roman(num: int) -> str:
    if not isinstance(num, int):
        raise ValueError("num must be an int")
    if not 1 <= num <= 3999:
        raise ValueError("num must be in the inclusive range [1, 3999]")
    
    val_to_sym = [
        (1000, "M"), (900, "CM"), (500, "D"), (400, "CD"),
        (100, "C"), (90, "XC"), (50, "L"), (40, "XL"),
        (10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I")
    ]
    
    roman = []
    for value, symbol in val_to_sym:
        while num >= value:
            roman.append(symbol)
            num -= value
    
    return "".join(roman)
