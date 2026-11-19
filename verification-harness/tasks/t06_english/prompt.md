Write a Python function `int_to_english(n: int) -> str` that spells out an integer in English words.

Rules:

- `n` must be in the range `0 <= n <= 999_999_999`. Raise `ValueError` otherwise.
- Use lowercase words separated by single spaces. Do not use "and" or commas.
- Write numbers 21–99 that are not multiples of ten with a hyphen: `"twenty-one"`, `"ninety-nine"`.
- Use the scale words `"hundred"`, `"thousand"` and `"million"`. Leave out groups that are zero.
- `0` is `"zero"`; zero never appears inside a larger number.

Examples:

- `int_to_english(105)` → `"one hundred five"`
- `int_to_english(12345)` → `"twelve thousand three hundred forty-five"`
- `int_to_english(1000001)` → `"one million one"`
