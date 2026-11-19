PAIRS = [(1000, "M"), (900, "CM"), (500, "D"), (400, "CD"), (100, "C"), (90, "XC"),
         (50, "L"), (40, "XL"), (10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I")]


def _to_roman(n):
    out = []
    for value, symbol in PAIRS:
        count, n = divmod(n, value)
        out.append(symbol * count)
    return "".join(out)


# Every valid numeral is the canonical spelling of exactly one number.
CANONICAL = {_to_roman(n): n for n in range(1, 4000)}


def parse_roman(s: str) -> int:
    if s not in CANONICAL:
        raise ValueError(f"not a valid Roman numeral: {s!r}")
    return CANONICAL[s]
