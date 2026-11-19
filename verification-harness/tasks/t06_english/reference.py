ONES = ("zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen "
        "fifteen sixteen seventeen eighteen nineteen").split()
TENS = "_ _ twenty thirty forty fifty sixty seventy eighty ninety".split()


def _below_thousand(n: int) -> list[str]:
    words = []
    hundreds, rest = divmod(n, 100)
    if hundreds:
        words += [ONES[hundreds], "hundred"]
    if rest >= 20:
        tens, ones = divmod(rest, 10)
        words.append(TENS[tens] + (f"-{ONES[ones]}" if ones else ""))
    elif rest:
        words.append(ONES[rest])
    return words


def int_to_english(n: int) -> str:
    if not 0 <= n <= 999_999_999:
        raise ValueError(f"out of range: {n}")
    if n == 0:
        return "zero"
    millions, rest = divmod(n, 1_000_000)
    thousands, rest = divmod(rest, 1000)
    words = []
    if millions:
        words += _below_thousand(millions) + ["million"]
    if thousands:
        words += _below_thousand(thousands) + ["thousand"]
    words += _below_thousand(rest)
    return " ".join(words)
