from collections import OrderedDict


def simulate_cache(capacity: int, ops: list[tuple]) -> list:
    entries = OrderedDict()  # key -> (value, expires_at or None); last item = most recently used
    results = []

    def alive(key, now):
        expires = entries[key][1]
        return expires is None or now < expires

    for op in ops:
        if op[0] == "get":
            _, key, now = op
            if key in entries and alive(key, now):
                entries.move_to_end(key)
                results.append(entries[key][0])
            else:
                results.append(None)
        else:
            _, key, value, now, ttl = op
            for k in [k for k in entries if not alive(k, now)]:
                del entries[k]  # expired entries never count toward the capacity
            if key not in entries and len(entries) >= capacity:
                entries.popitem(last=False)
            entries[key] = (value, None if ttl is None else now + ttl)
            entries.move_to_end(key)
    return results
