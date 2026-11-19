Write a Python function `word_wrap(text: str, width: int) -> list[str]` that wraps text greedily.

- `width >= 1`. Words are maximal runs of non-whitespace characters (as returned by `text.split()`).
- Build lines from left to right. Put as many words on a line as fit, joined by single spaces,
  so that no line is longer than `width`. When the next word does not fit, start a new line.
- A word longer than `width` always starts on a new line. Cut it into pieces of exactly `width`
  characters, each on its own line. The last, shorter-or-equal piece becomes the start of the
  current line, and the following words may continue on that line if they fit.
- Text that is empty or contains only whitespace gives `[]`.

Examples:

- `word_wrap("the quick brown fox", 10)` → `["the quick", "brown fox"]`
- `word_wrap("supercalifragilistic is long", 6)` → `["superc", "alifra", "gilist", "ic is", "long"]`
- `word_wrap("hi abcdefgh", 4)` → `["hi", "abcd", "efgh"]`
