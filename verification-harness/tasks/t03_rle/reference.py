from itertools import groupby


def rle_encode(s: str) -> str:
    return "".join(f"{ch}{len(list(run))}" for ch, run in groupby(s))
