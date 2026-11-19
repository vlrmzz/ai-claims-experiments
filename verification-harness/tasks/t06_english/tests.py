FUNCTION = "int_to_english"
DIFFICULTY = "medium"

CASES = [
    ((0,), "zero"),
    ((13,), "thirteen"),
    ((21,), "twenty-one"),
    ((40,), "forty"),
    ((90,), "ninety"),
    ((100,), "one hundred"),
    ((105,), "one hundred five"),
    ((1000,), "one thousand"),
    ((1010,), "one thousand ten"),
    ((12345,), "twelve thousand three hundred forty-five"),
    ((1000001,), "one million one"),
    ((1100000,), "one million one hundred thousand"),
    ((20000019,), "twenty million nineteen"),
    ((999999999,), "nine hundred ninety-nine million nine hundred ninety-nine thousand nine hundred ninety-nine"),
    ((-1,), ValueError),
    ((1000000000,), ValueError),
]
