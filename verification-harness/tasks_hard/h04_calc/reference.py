import re
from fractions import Fraction

TOKEN = re.compile(r"\s*(?:(\d+)|(.))")


def _tokenize(expr):
    tokens = []
    for number, op in TOKEN.findall(expr):
        if number:
            tokens.append(Fraction(int(number)))
        elif op.strip():
            if op not in "+-*/^()":
                raise ValueError(f"unexpected character {op!r}")
            tokens.append(op)
    return tokens


def evaluate(expr: str) -> str:
    tokens = _tokenize(expr)
    pos = 0

    def peek():
        return tokens[pos] if pos < len(tokens) else None

    def take():
        nonlocal pos
        if pos >= len(tokens):
            raise ValueError("unexpected end of expression")
        pos += 1
        return tokens[pos - 1]

    def expression():  # expression := term (('+' | '-') term)*
        value = term()
        while peek() in ("+", "-"):
            value = value + term() if take() == "+" else value - term()
        return value

    def term():  # term := unary (('*' | '/') unary)*
        value = unary()
        while peek() in ("*", "/"):
            if take() == "*":
                value *= unary()
            else:
                divisor = unary()
                if divisor == 0:
                    raise ZeroDivisionError("division by zero")
                value /= divisor
        return value

    def unary():  # unary := ('-' | '+') unary | power
        if peek() in ("-", "+"):
            return -unary() if take() == "-" else unary()
        return power()

    def power():  # power := atom ('^' unary)?  -- right-associative through unary -> power
        base = atom()
        if peek() == "^":
            take()
            exponent = unary()
            if exponent.denominator != 1:
                raise ValueError("exponent must be an integer")
            if base == 0 and exponent < 0:
                raise ZeroDivisionError("zero to a negative power")
            return base ** int(exponent)
        return base

    def atom():  # atom := number | '(' expression ')'
        token = take()
        if isinstance(token, Fraction):
            return token
        if token == "(":
            value = expression()
            if take() != ")":
                raise ValueError("expected ')'")
            return value
        raise ValueError(f"unexpected token {token!r}")

    result = expression()
    if pos != len(tokens):
        raise ValueError(f"unexpected token {tokens[pos]!r}")
    return str(result.numerator) if result.denominator == 1 else f"{result.numerator}/{result.denominator}"
