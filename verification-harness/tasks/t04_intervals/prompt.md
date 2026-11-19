Write a Python function `merge_intervals(intervals: list[list[int]]) -> list[list[int]]`.

Each interval is a two-element list `[start, end]` with `start <= end` (both inclusive).
The input may be in any order. Merge every group of intervals that overlap, and also merge
intervals that only touch (for example `[1, 2]` and `[2, 3]` become `[1, 3]`).

Return a new list of two-element lists, sorted by start. An empty input gives `[]`.

Examples:

- `merge_intervals([[1, 3], [2, 6], [8, 10], [15, 18]])` → `[[1, 6], [8, 10], [15, 18]]`
- `merge_intervals([[1, 4], [4, 5]])` → `[[1, 5]]`
