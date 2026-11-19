Write a Python function `compare_versions(a: str, b: str) -> int`.

A version string is one or more non-negative integers separated by dots, for example `"1.10.3"`.
Compare the two versions component by component, numerically, from left to right:

- Leading zeros do not matter: `"1.01"` equals `"1.1"`.
- A missing component counts as `0`: `"1.0"` equals `"1"` and `"1.0.0"`.

Return `-1` if `a < b`, `1` if `a > b`, and `0` if they are equal.

Examples:

- `compare_versions("1.10", "1.9")` → `1`
- `compare_versions("1.0", "1.0.0")` → `0`
