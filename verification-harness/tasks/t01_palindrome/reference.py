def is_palindrome(s: str) -> bool:
    chars = [c.lower() for c in s if c.isalnum()]
    return chars == chars[::-1]
