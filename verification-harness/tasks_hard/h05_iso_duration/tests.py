FUNCTION = "iso_duration_seconds"
DIFFICULTY = "hard"

# CASES: the harness sees these. HIDDEN: held out, used only for scoring.
CASES = [
    (("PT36H",), 129600),
    (("P1DT12H",), 129600),
    (("PT1.5M",), 90),
    (("P1H",), ValueError),
]

HIDDEN = [
    (("P1Y2M10DT2H30M",), 37_593_000),
    (("P3W",), 1_814_400),
    (("P1M",), 2_592_000),
    (("PT1M",), 60),
    (("PT0S",), 0),
    (("P0D",), 0),
    (("PT0,5M",), 30),
    (("P1DT0.5H",), 88_200),
    (("PT1M30.0S",), 90),
    (("P2Y",), 63_072_000),
    (("PT100000S",), 100_000),
    (("P",), ValueError),
    (("PT",), ValueError),
    (("P1YT",), ValueError),
    (("PT1D",), ValueError),
    (("P1M2Y",), ValueError),
    (("PT1S2M",), ValueError),
    (("P1Y1Y",), ValueError),
    (("P1.5Y2M",), ValueError),
    (("PT1.5H30M",), ValueError),
    (("P1W2D",), ValueError),
    (("P1WT1H",), ValueError),
    (("1Y",), ValueError),
    (("p1y",), ValueError),
    (("P1y",), ValueError),
    (("P-1D",), ValueError),
    (("PT1.H",), ValueError),
    (("PT.5H",), ValueError),
    ((" P1D",), ValueError),
    (("P1D ",), ValueError),
    (("PT1H 30M",), ValueError),
    (("",), ValueError),
]
