Write a Python function `iso_duration_seconds(s: str) -> int` that parses an ISO 8601 duration
and returns its length in seconds, using these fixed conversions: a year is 365 days, a month is
30 days, a week is 7 days, a day is 86400 seconds.

Format:

- The string starts with `P`. After it comes an optional date part, then an optional time part.
- The date part is up to three components in this order: years `Y`, months `M`, days `D`.
  Weeks `W` are allowed only on their own: `P3W` is valid, but `W` cannot be combined with any other component.
- The time part starts with `T`, followed by up to three components in this order: hours `H`,
  minutes `M`, seconds `S`. `M` means months before `T` and minutes after it.
- Each component is a number followed by its letter. Each letter appears at most once, and order matters.
- At least one component must be present, and a `T` must be followed by at least one component.
- Numbers are non-negative decimal integers. The last component in the string (and only the last
  one) may have a fractional part, written with `.` or `,` and with at least one digit on each side
  of it. Inputs with a fraction always come to a whole number of seconds.
- Letters are uppercase. No signs, spaces or other characters are allowed.

Raise `ValueError` for any string that does not follow this format.

Examples:

- `iso_duration_seconds("PT36H")` → `129600`
- `iso_duration_seconds("P1DT12H")` → `129600`
- `iso_duration_seconds("PT1.5M")` → `90`
