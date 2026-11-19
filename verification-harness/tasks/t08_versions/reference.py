from itertools import zip_longest


def compare_versions(a: str, b: str) -> int:
    for x, y in zip_longest(a.split("."), b.split("."), fillvalue="0"):
        if int(x) != int(y):
            return 1 if int(x) > int(y) else -1
    return 0
