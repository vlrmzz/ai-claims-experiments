def parse_csv_line(line: str) -> list[str]:
    fields = []
    i, n = 0, len(line)
    while True:
        if i < n and line[i] == '"':
            i += 1
            chars = []
            while True:
                if i >= n:
                    raise ValueError("unterminated quoted field")
                if line[i] == '"':
                    if i + 1 < n and line[i + 1] == '"':
                        chars.append('"')
                        i += 2
                        continue
                    i += 1
                    break
                chars.append(line[i])
                i += 1
            if i < n and line[i] != ",":
                raise ValueError("unexpected character after closing quote")
            fields.append("".join(chars))
        else:
            end = line.find(",", i)
            end = n if end == -1 else end
            field = line[i:end]
            if '"' in field:
                raise ValueError("quote inside an unquoted field")
            fields.append(field)
            i = end
        if i >= n:
            return fields
        i += 1  # skip the comma; a trailing comma leaves one more (empty) field
