import re


def camel_to_snake(name: str) -> str:
    name = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", name)  # rule 2: acronym boundary
    name = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", name)  # rule 1: lower/digit -> upper
    return name.lower()
