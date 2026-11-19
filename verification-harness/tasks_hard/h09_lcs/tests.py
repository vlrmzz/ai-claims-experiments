FUNCTION = "smallest_lcs"
DIFFICULTY = "hard"

import random

_rng = random.Random(7)
_A = "".join(_rng.choice("abcd") for _ in range(300))
_B = "".join(_rng.choice("abcd") for _ in range(300))

# CASES: the harness sees these. HIDDEN: held out, used only for scoring.
CASES = [
    (("abcbdab", "bdcaba"), "bcab"),
    (("abc", "def"), ""),
    (("aaa", "aa"), "aa"),
]

HIDDEN = [
    (("", ""), ""),
    (("ab", "ba"), "a"),
    (("zyx", "xyz"), "x"),
    (("cbabc", "bcacb"), "bab"),
    (("baab", "abba"), "aa"),
    (("acbdcb", "cabdbc"), "abdb"),
    (("xaxbx", "bxaxa"), "xax"),
    (("thequickbrownfox", "foxjumpsoverquick"), "equick"),
    ((_A, _B), 'cbdacbaaddadaabaaabcdbacabcaaabcdccbbbacccdbcbddacccaacdaadccadbdabcbbacddcbbaacabdccbaddadbabaaabcaddaadcaaaacacbbbddadcababcbdadcabdcdddabaddcbbaabccbcacddababdaacdaacaadaacbbcdbdada'),
]
