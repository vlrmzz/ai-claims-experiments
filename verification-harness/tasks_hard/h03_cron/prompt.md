Write a Python function `next_cron(expr: str, after: str) -> str` that returns the first time
strictly after `after` that matches the cron expression `expr`.

Times are strings in the form `YYYY-MM-DDTHH:MM` (for example `2024-01-31T09:05`), with no
seconds and no time zone. Return the result in the same form.

`expr` has exactly five fields separated by single spaces: minute (0–59), hour (0–23),
day of month (1–31), month (1–12) and day of week (0–7, where both 0 and 7 mean Sunday and 1 is Monday).

Each field is a comma-separated list of one or more items. An item is one of:

- `*`: every value in the field's range
- `N`: a single value
- `A-B`: every value from A to B inclusive, where A <= B
- `*/S` or `A-B/S`: every S-th value of `*` or of `A-B`, starting at its first value (S >= 1)

Day matching follows classic cron: if the day-of-month field and the day-of-week field both do
not start with `*`, a day matches when either of them matches. Otherwise a day must match both
(a field that starts with `*`, such as `*` or `*/2`, still restricts by its own values).

Raise `ValueError` if the expression is malformed (wrong number of fields, a value out of range,
`A > B`, a step of 0, or anything else not described above) or if no matching time exists within
the 8 years after `after`.

Examples:

- `next_cron("*/15 * * * *", "2024-01-01T10:07")` → `"2024-01-01T10:15"`
- `next_cron("0 9 * * 1-5", "2024-01-05T09:00")` → `"2024-01-08T09:00"` (Friday to Monday)
