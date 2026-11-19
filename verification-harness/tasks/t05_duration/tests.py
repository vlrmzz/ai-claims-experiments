FUNCTION = "parse_duration"
DIFFICULTY = "medium"

CASES = [
    (("1h30m",), 5400),
    (("45s",), 45),
    (("2d",), 172800),
    (("1d2h3m4s",), 93784),
    (("0s",), 0),
    (("90m",), 5400),
    (("1d1s",), 86401),
    (("007m",), 420),
    (("",), ValueError),
    (("10",), ValueError),
    (("1x",), ValueError),
    (("h",), ValueError),
    (("1h1h",), ValueError),
    (("30m1h",), ValueError),
    (("1h 30m",), ValueError),
    ((" 1h",), ValueError),
    (("1.5h",), ValueError),
    (("-1h",), ValueError),
    (("1H",), ValueError),
    (("1h30",), ValueError),
]
