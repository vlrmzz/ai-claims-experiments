Write a Python function `parse_duration(s: str) -> int` that converts a compact duration string
to a number of seconds.

The format is one or more components written together with no separators. Each component is a
non-negative integer (ASCII digits only) followed by one unit letter:

- `d` = days (86400 s), `h` = hours (3600 s), `m` = minutes (60 s), `s` = seconds

Rules:

- Units must appear in the order `d`, `h`, `m`, `s`. Each unit may appear at most once. Any unit may be left out.
- Values are not normalised: `"90m"` is valid and means 5400.
- Unit letters are lowercase only. No whitespace, signs or decimal points are allowed anywhere.

Raise `ValueError` for any string that does not follow this format, including the empty string,
a number without a unit, a unit without a number, an unknown unit, a repeated unit, and units out of order.

Examples:

- `parse_duration("1h30m")` → `5400`
- `parse_duration("1d2h3m4s")` → `93784`
- `parse_duration("30m1h")` → raises `ValueError`
