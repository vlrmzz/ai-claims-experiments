FUNCTION = "is_palindrome"
DIFFICULTY = "easy"

# (args, expected). An exception class as `expected` means the call must raise it.
CASES = [
    (("A man, a plan, a canal: Panama",), True),
    (("race a car",), False),
    (("",), True),
    ((".,!",), True),
    (("0P",), False),
    (("Was it a car or a cat I saw?",), True),
    (("ab_a",), True),
    (("No 'x' in Nixon",), True),
    (("abca",), False),
    (("Ünü",), True),
]
