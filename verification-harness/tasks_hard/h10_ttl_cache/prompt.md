Write a Python function `simulate_cache(capacity: int, ops: list[tuple]) -> list` that simulates
a least-recently-used (LRU) cache whose entries can expire, and returns the result of every `get`.

`capacity >= 1` is the maximum number of entries. `ops` is a list of operations, applied in order,
with non-decreasing integer times:

- `("put", key, value, time, ttl)` stores `value` under `key`. `ttl` is a positive integer or `None`.
  The entry expires at `time + ttl`; with `ttl=None` it never expires.
- `("get", key, time)` looks up `key`.

Rules:

- An entry is expired at every time `t >= time + ttl`. An expired entry is never returned.
- `get` returns the stored value, or `None` if the key is missing or expired. A successful `get`
  makes the entry the most recently used one. It does not change its expiry time.
- `put` on a key that is present and not expired replaces its value and its expiry, and makes it
  the most recently used one. This never evicts anything.
- `put` of a new key (or of a key whose entry has expired) when the cache already holds `capacity`
  entries that are present and not expired: first evict the least recently used of them, then insert.
  Expired entries never count toward the capacity.
- Recency is set only by `put` and successful `get`.

Return a list with one item per `get`, in order. `put` adds nothing to the list.

Example:

```python
simulate_cache(2, [
    ("put", "a", 1, 0, None),
    ("put", "b", 2, 1, None),
    ("get", "a", 2),          # 1; "a" is now the most recently used
    ("put", "c", 3, 3, None), # cache is full: evicts "b"
    ("get", "b", 4),          # None
    ("get", "c", 5),          # 3
])
# → [1, None, 3]
```
