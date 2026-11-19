Write a Python function `sort_versions(versions: list[str]) -> list[str]` that sorts version strings
in ascending order of Semantic Versioning 2.0.0 precedence.

A valid version has the form `MAJOR.MINOR.PATCH`, optionally followed by `-PRERELEASE`, optionally
followed by `+BUILD`:

- `MAJOR`, `MINOR` and `PATCH` are non-negative integers written without leading zeros (`0` is allowed, `01` is not).
- `PRERELEASE` is one or more identifiers separated by dots. Each identifier is non-empty and uses only
  `[0-9A-Za-z-]`. An identifier made only of digits is numeric and must not have leading zeros.
- `BUILD` is one or more identifiers separated by dots. Each identifier is non-empty and uses only
  `[0-9A-Za-z-]`. Leading zeros are allowed here.
- Nothing else is allowed: no `v` prefix, no whitespace.

If any string in the list is not valid, raise `ValueError`.

Precedence:

1. Compare `MAJOR`, `MINOR` and `PATCH` numerically, in that order.
2. If those are equal, a version with a pre-release has lower precedence than the same version without one.
3. Compare two pre-releases identifier by identifier, from left to right: numeric identifiers compare
   numerically; other identifiers compare lexically in ASCII order; a numeric identifier has lower
   precedence than a non-numeric one. If all compared identifiers are equal, the version with more
   identifiers has higher precedence.
4. `BUILD` is ignored for precedence. Versions with equal precedence keep their order from the input.

Example:

```python
sort_versions(["1.0.0", "1.0.0-rc.1", "1.0.0-alpha", "1.0.0-beta.11", "1.0.0-beta.2",
               "1.0.0-alpha.beta", "1.0.0-beta", "1.0.0-alpha.1"])
# → ["1.0.0-alpha", "1.0.0-alpha.1", "1.0.0-alpha.beta", "1.0.0-beta", "1.0.0-beta.2",
#    "1.0.0-beta.11", "1.0.0-rc.1", "1.0.0"]
```
