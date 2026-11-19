import re

PATTERN = re.compile(r"(?:([0-9]+)d)?(?:([0-9]+)h)?(?:([0-9]+)m)?(?:([0-9]+)s)?")
SECONDS = (86400, 3600, 60, 1)


def parse_duration(s: str) -> int:
    match = PATTERN.fullmatch(s)
    if not s or match is None:
        raise ValueError(f"invalid duration: {s!r}")
    return sum(int(value) * unit for value, unit in zip(match.groups(), SECONDS) if value is not None)
