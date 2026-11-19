FUNCTION = "simulate_cache"
DIFFICULTY = "medium"

# CASES: the harness sees these. HIDDEN: held out, used only for scoring.
CASES = [
    ((2, [("put", "a", 1, 0, None), ("put", "b", 2, 1, None), ("get", "a", 2),
          ("put", "c", 3, 3, None), ("get", "b", 4), ("get", "c", 5)]),
     [1, None, 3]),
    ((1, [("put", "a", 1, 0, 5), ("get", "a", 4), ("get", "a", 5)]),
     [1, None]),
]

HIDDEN = [
    # Expiry is exclusive at time + ttl, and a get does not extend it.
    ((2, [("put", "a", 1, 0, 10), ("get", "a", 9), ("get", "a", 9), ("get", "a", 10)]),
     [1, 1, None]),
    # An expired entry does not count toward capacity, so nothing live is evicted.
    ((2, [("put", "a", 1, 0, 3), ("put", "b", 2, 1, None), ("put", "c", 3, 5, None),
          ("get", "b", 6), ("get", "c", 6), ("get", "a", 6)]),
     [2, 3, None]),
    # Re-putting an existing key never evicts, and refreshes its recency.
    ((2, [("put", "a", 1, 0, None), ("put", "b", 2, 0, None), ("put", "a", 10, 1, None),
          ("put", "c", 3, 2, None), ("get", "a", 3), ("get", "b", 3), ("get", "c", 3)]),
     [10, None, 3]),
    # Re-putting replaces the expiry: a shorter ttl makes it expire sooner.
    ((2, [("put", "a", 1, 0, None), ("put", "a", 2, 1, 2), ("get", "a", 2), ("get", "a", 3)]),
     [2, None]),
    # Re-putting an expired key counts as a new key.
    ((1, [("put", "a", 1, 0, 1), ("put", "a", 2, 5, None), ("get", "a", 6)]),
     [2]),
    # A failed get (missing or expired) does not change recency.
    ((2, [("put", "a", 1, 0, None), ("put", "b", 2, 1, None), ("get", "zz", 2),
          ("put", "c", 3, 3, None), ("get", "a", 4), ("get", "b", 4)]),
     [None, None, 2]),
    # Values may be falsy; None is only for a miss.
    ((2, [("put", "a", 0, 0, None), ("put", "b", "", 0, None), ("get", "a", 1), ("get", "b", 1)]),
     [0, ""]),
    # LRU order with several gets.
    ((3, [("put", 1, "x", 0, None), ("put", 2, "y", 0, None), ("put", 3, "z", 0, None),
          ("get", 1, 1), ("get", 2, 1), ("put", 4, "w", 2, None),
          ("get", 3, 3), ("get", 1, 3), ("get", 2, 3), ("get", 4, 3)]),
     ["x", "y", None, "x", "y", "w"]),
    # Several expired entries at once free several slots.
    ((2, [("put", "a", 1, 0, 2), ("put", "b", 2, 0, 2), ("put", "c", 3, 2, None),
          ("put", "d", 4, 2, None), ("get", "c", 3), ("get", "d", 3)]),
     [3, 4]),
    ((1, []), []),
]
