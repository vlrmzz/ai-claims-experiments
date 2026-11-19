def eval_rpn(tokens: list[str]) -> int:
    stack: list[int] = []
    for token in tokens:
        if token in {"+", "-", "*", "/"}:
            b = stack.pop()
            a = stack.pop()
            if token == "+":
                stack.append(a + b)
            elif token == "-":
                stack.append(a - b)
            elif token == "*":
                stack.append(a * b)
            else:
                # Exact truncation toward zero; int(a / b) would go through a float.
                q = abs(a) // abs(b)
                stack.append(q if (a < 0) == (b < 0) else -q)
        else:
            stack.append(int(token))
    return stack[0]
