Write a Python function `is_palindrome(s: str) -> bool`.

It returns `True` if `s` reads the same forwards and backwards after you:

- drop every character for which `str.isalnum()` is `False`, and
- convert the remaining characters to lowercase.

An empty string (or a string with no alphanumeric characters) counts as a palindrome.

Examples:

- `is_palindrome("A man, a plan, a canal: Panama")` → `True`
- `is_palindrome("race a car")` → `False`
- `is_palindrome("")` → `True`
