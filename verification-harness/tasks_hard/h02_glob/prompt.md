Write a Python function `glob_match(pattern: str, path: str) -> bool` that reports whether a
slash-separated `path` matches a glob `pattern`. The pattern must match the whole path. Matching
is case-sensitive. Paths never start or end with `/` and never contain `//`.

Pattern syntax:

- `?` matches exactly one character other than `/`.
- `*` matches any sequence of characters other than `/`, including the empty sequence.
- `**` is special only when it is a whole path segment: the whole pattern, or at the start followed
  by `/`, or between two `/`, or at the end after a `/`. Such a `**` segment matches zero or more
  whole path segments. So `a/**/b` matches `a/b`, `a/x/b` and `a/x/y/b`; `**/b` matches `b` and
  `x/y/b`; `a/**` matches `a`, `a/x` and `a/x/y`; and `**` matches any path. A `**` that is not a
  whole segment (as in `a**b`) behaves like `*`.
- `[...]` matches one character, other than `/`, from the set. `a-z` inside the brackets is a range.
  If the first character after `[` is `!`, the set is negated. A `]` right after `[` or `[!` is a
  literal `]`, and a `-` that is first or last in the set is a literal `-`. No other character is
  special inside the brackets. A `[` with no closing `]` is a literal `[`.
- `\` makes the next character literal, so `\*` matches only `*`. A pattern that ends with a single
  unpaired `\` is invalid: raise `ValueError`.
- Every other character matches itself.

Examples:

- `glob_match("src/*.py", "src/main.py")` → `True`
- `glob_match("src/*.py", "src/lib/main.py")` → `False`
- `glob_match("src/**/*.py", "src/main.py")` → `True`
