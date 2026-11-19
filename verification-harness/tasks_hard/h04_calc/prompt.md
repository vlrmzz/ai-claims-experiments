Write a Python function `evaluate(expr: str) -> str` that evaluates an arithmetic expression
exactly, using rational numbers, and returns the result as a string.

Syntax:

- Numbers are non-negative integer literals (digits only; no decimal points).
- Binary operators: `+`, `-`, `*`, `/` and `^` (power). Parentheses group.
- Unary `-` and unary `+` are allowed, and may repeat (`--3` is `3`).
- Spaces may appear anywhere between tokens and are ignored. No other characters are allowed.

Precedence, from highest to lowest:

1. `^`, which is right-associative: `2^3^2` is `2^(3^2)` = 512.
2. Unary `-` and `+`. They bind more loosely than `^`, so `-2^2` is `-(2^2)` = -4. The exponent
   of `^` may itself start with a unary sign: `2^-1` is 1/2.
3. `*` and `/`, left-associative.
4. `+` and `-`, left-associative.

Rules:

- `/` is exact division: `7/2` is the fraction 7/2.
- The exponent must be an integer value; otherwise raise `ValueError`. `0^0` is 1.
- Division by zero, including `0` raised to a negative power, raises `ZeroDivisionError`.
- Any syntax error raises `ValueError`: an empty expression, unbalanced parentheses, a missing
  operand, two numbers in a row (`2 3`), or implicit multiplication (`2(3)`).

Output: the result in lowest terms, as `"n"` if it is an integer and as `"n/d"` otherwise, with
`d > 0` and the sign on `n` (for example `"-2/3"`).

Examples:

- `evaluate("1 + 2 * 3")` → `"7"`
- `evaluate("7 / 2")` → `"7/2"`
- `evaluate("2 ^ 3 ^ 2")` → `"512"`
