FUNCTION = "parse_csv_line"
DIFFICULTY = "medium"

# CASES: the harness sees these. HIDDEN: held out, used only for scoring.
CASES = [
    (('a,"b,c",d',), ["a", "b,c", "d"]),
    (('"say ""hi"""',), ['say "hi"']),
    (("a,,",), ["a", "", ""]),
    (("a,b,c",), ["a", "b", "c"]),
]

HIDDEN = [
    (("",), [""]),
    ((",",), ["", ""]),
    (('""',), [""]),
    (('"",""',), ["", ""]),
    ((" a , b ",), [" a ", " b "]),
    (('"a",',), ["a", ""]),
    (('x,"y"',), ["x", "y"]),
    (('"a""b",c',), ['a"b', "c"]),
    (('""""',), ['"']),
    (('"a,b,c"',), ["a,b,c"]),
    (('"  "',), ["  "]),
    (('a"b',), ValueError),
    (('"abc',), ValueError),
    (('"a"b',), ValueError),
    (('"a" ,b',), ValueError),
    ((' "a"',), ValueError),
    (('a,"b',), ValueError),
    (('"a""',), ValueError),
    (('a,b"',), ValueError),
]
