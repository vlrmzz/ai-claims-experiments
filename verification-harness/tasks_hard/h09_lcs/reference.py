def smallest_lcs(a: str, b: str) -> str:
    n, m = len(a), len(b)
    # suffix[i][j] = length of an LCS of a[i:] and b[j:]
    suffix = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n - 1, -1, -1):
        for j in range(m - 1, -1, -1):
            suffix[i][j] = suffix[i + 1][j + 1] + 1 if a[i] == b[j] else max(suffix[i + 1][j], suffix[i][j + 1])

    # Build the answer greedily: at each step take the smallest character that can still start an
    # LCS of the remaining length, using its earliest occurrence in both strings.
    out, i, j = [], 0, 0
    remaining = suffix[0][0]
    while remaining:
        for ch in sorted(set(a[i:]) & set(b[j:])):
            pi, pj = a.index(ch, i), b.index(ch, j)
            if suffix[pi + 1][pj + 1] == remaining - 1:
                out.append(ch)
                i, j, remaining = pi + 1, pj + 1, remaining - 1
                break
    return "".join(out)
