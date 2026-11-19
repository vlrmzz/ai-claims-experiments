FUNCTION = "rle_encode"
DIFFICULTY = "easy"

CASES = [
    (("aaabccdddd",), "a3b1c2d4"),
    (("",), ""),
    (("a",), "a1"),
    (("abc",), "a1b1c1"),
    (("a" * 12,), "a12"),
    (("aAaa",), "a1A1a2"),
    (("zzzzzzzzzzzb",), "z11b1"),
    (("abba",), "a1b2a1"),
]
