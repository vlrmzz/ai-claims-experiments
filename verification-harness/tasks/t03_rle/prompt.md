Write a Python function `rle_encode(s: str) -> str` (run-length encoding).

`s` contains only ASCII letters. Replace each maximal run of the same character with that
character followed by the length of the run in decimal. Always write the count, even when it is 1.
The comparison is case-sensitive. An empty input gives an empty output.

Examples:

- `rle_encode("aaabccdddd")` → `"a3b1c2d4"`
- `rle_encode("a")` → `"a1"`
- `rle_encode("")` → `""`
