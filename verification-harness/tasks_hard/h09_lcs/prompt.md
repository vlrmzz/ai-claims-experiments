Write a Python function `smallest_lcs(a: str, b: str) -> str` that returns a longest common
subsequence of `a` and `b`. When several different longest common subsequences exist, return the
one that comes first in lexicographic order (plain string comparison in Python).

A subsequence keeps the characters in order but may skip characters. Both strings have at most
300 characters, and the function must finish within a second for inputs of that size. If the
strings have no character in common, return `""`.

Examples:

- `smallest_lcs("abcbdab", "bdcaba")` → `"bcab"` (the other longest ones, `"bcba"` and `"bdab"`, come later)
- `smallest_lcs("abc", "def")` → `""`
