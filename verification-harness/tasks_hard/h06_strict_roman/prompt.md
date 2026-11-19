Write a Python function `parse_roman(s: str) -> int` that converts a Roman numeral to an integer
and rejects anything that is not a correctly written numeral.

A string is valid only if it is exactly the standard way to write some integer from 1 to 3999,
using uppercase `I V X L C D M`:

- Thousands are `M`, `MM` or `MMM`.
- Each of the hundreds, tens and units is written with the usual forms, for example for the units
  `I II III IV V VI VII VIII IX` (and likewise `X…XC` for tens and `C…CM` for hundreds).
- Only these subtractive pairs exist: `IV IX XL XC CD CM`.

Anything else raises `ValueError`: the empty string, lowercase letters, other characters,
four repeats such as `IIII`, repeated `V`, `L` or `D`, other subtractions such as `IC`, `VX` or `IL`,
and symbols in the wrong order.

Examples:

- `parse_roman("MCMXCIV")` → `1994`
- `parse_roman("IIII")` → raises `ValueError`
