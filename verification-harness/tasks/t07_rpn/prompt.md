Write a Python function `eval_rpn(tokens: list[str]) -> int` that evaluates an integer expression
in Reverse Polish Notation.

- Each token is either an operator (`+`, `-`, `*`, `/`) or an integer literal, which may be negative (for example `"-11"`).
- Operators are binary; the left operand is the one pushed earlier.
- `/` is integer division that truncates toward zero (like C or Java), not toward negative infinity.
- Integers can be arbitrarily large, and every result must be exact.
- You can assume the expression is valid and never divides by zero.

Examples:

- `eval_rpn(["2", "1", "+", "3", "*"])` → `9`
- `eval_rpn(["4", "13", "5", "/", "+"])` → `6`
