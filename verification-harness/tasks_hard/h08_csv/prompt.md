Write a Python function `parse_csv_line(line: str) -> list[str]` that splits one line of strict
CSV into its fields.

- Fields are separated by commas. A line with `k` commas outside quotes has `k + 1` fields; the
  empty string is one empty field: `[""]`.
- A field is quoted if its very first character is `"`. Inside a quoted field, `""` stands for one
  literal `"`, and every other character (including commas) is literal. The closing `"` must be
  followed directly by a comma or by the end of the line.
- An unquoted field is taken exactly as written, including spaces, and must not contain `"`.
- Nothing is trimmed. The line contains no newline characters.

Raise `ValueError` for a quoted field that is never closed, for a character other than a comma
after a closing quote, and for a `"` inside an unquoted field (including a field that starts with a
space and then has a quote).

Examples:

- `parse_csv_line('a,"b,c",d')` → `["a", "b,c", "d"]`
- `parse_csv_line('"say ""hi"""')` → `['say "hi"']`
- `parse_csv_line('a,,')` → `["a", "", ""]`
