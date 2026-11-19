Write a Python function `humanize_bytes(n: int) -> str` that formats a byte count with binary units.

- Units, in order: `B`, `KiB`, `MiB`, `GiB`, `TiB`, `PiB`, `EiB`, each 1024 times the previous one.
- If `abs(n) < 1024`, return the integer followed by ` B`, for example `"1023 B"` or `"-5 B"`.
- Otherwise use the largest unit whose size is at most `abs(n)` (never larger than `EiB`), and
  show the value with exactly one digit after the decimal point, for example `"1.5 KiB"`.
- Round the value to one decimal place with round-half-up on the exact value: 1.25 KiB is
  `"1.3 KiB"`. (Python's `round()` and `format()` do not do this.)
- If rounding gives 1024.0 and a larger unit exists, show `"1.0"` in the next unit instead.
- For negative `n`, format `abs(n)` and put a `-` in front.

Examples:

- `humanize_bytes(1536)` → `"1.5 KiB"`
- `humanize_bytes(1048576)` → `"1.0 MiB"`
- `humanize_bytes(-2048)` → `"-2.0 KiB"`
