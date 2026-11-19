FUNCTION = "parse_roman"
DIFFICULTY = "medium"

# CASES: the harness sees these. HIDDEN: held out, used only for scoring.
CASES = [
    (("MCMXCIV",), 1994),
    (("III",), 3),
    (("IIII",), ValueError),
]

HIDDEN = [
    (("MMMCMXCIX",), 3999),
    (("I",), 1),
    (("XLIX",), 49),
    (("CDXLIV",), 444),
    (("MMXXIV",), 2024),
    (("",), ValueError),
    (("iv",), ValueError),
    (("MMMM",), ValueError),
    (("VV",), ValueError),
    (("LL",), ValueError),
    (("DD",), ValueError),
    (("IC",), ValueError),
    (("VX",), ValueError),
    (("IL",), ValueError),
    (("XM",), ValueError),
    (("IIX",), ValueError),
    (("IXI",), ValueError),
    (("XCX",), ValueError),
    (("CMC",), ValueError),
    (("IVI",), ValueError),
    (("VIV",), ValueError),
    (("XXXX",), ValueError),
    (("MCMC",), ValueError),
    (("IM",), ValueError),
    (("X I",), ValueError),
    (("A",), ValueError),
]
