import re


def _translate(pattern: str) -> str:
    out = []
    i, n = 0, len(pattern)
    while i < n:
        at_segment_start = i == 0 or pattern[i - 1] == "/"
        if pattern == "**":
            return ".*"
        if at_segment_start and pattern.startswith("**/", i):
            out.append("(?:[^/]+/)*")  # zero or more whole segments, each with its slash
            i += 3
        elif i > 0 and pattern[i:] == "/**":
            out.append("(?:/[^/]+)*")
            i = n
        elif pattern[i] == "*":
            while i < n and pattern[i] == "*":
                i += 1
            out.append("[^/]*")
        elif pattern[i] == "?":
            out.append("[^/]")
            i += 1
        elif pattern[i] == "\\":
            if i + 1 == n:
                raise ValueError("pattern ends with an unpaired backslash")
            out.append(re.escape(pattern[i + 1]))
            i += 2
        elif pattern[i] == "[":
            j = i + 1
            if j < n and pattern[j] == "!":
                j += 1
            if j < n and pattern[j] == "]":
                j += 1
            close = pattern.find("]", j)
            if close == -1:
                out.append(re.escape("["))
                i += 1
                continue
            body = pattern[i + 1:close]
            negate = body.startswith("!")
            if negate:
                body = body[1:]
            items = "".join(
                "-" if ch == "-" and 0 < k < len(body) - 1 else re.escape(ch) for k, ch in enumerate(body)
            )
            out.append(f"[^/{items}]" if negate else f"(?!/)[{items}]")
            i = close + 1
        else:
            out.append(re.escape(pattern[i]))
            i += 1
    return "".join(out)


def glob_match(pattern: str, path: str) -> bool:
    return re.fullmatch(_translate(pattern), path, re.DOTALL) is not None
