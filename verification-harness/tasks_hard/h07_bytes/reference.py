UNITS = ["B", "KiB", "MiB", "GiB", "TiB", "PiB", "EiB"]


def humanize_bytes(n: int) -> str:
    sign, n = ("-" if n < 0 else ""), abs(n)
    if n < 1024:
        return f"{sign}{n} B"
    k = 1
    while k + 1 < len(UNITS) and n >= 1024 ** (k + 1):
        k += 1
    size = 1024 ** k
    tenths = (20 * n + size) // (2 * size)  # round half up, in exact integer arithmetic
    if tenths == 10240 and k + 1 < len(UNITS):
        k, tenths = k + 1, 10
    return f"{sign}{tenths // 10}.{tenths % 10} {UNITS[k]}"
