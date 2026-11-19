import re
from fractions import Fraction

N = r"(\d+(?:[.,]\d+)?)"
PATTERN = re.compile(
    rf"P(?:{N}W|(?:{N}Y)?(?:{N}M)?(?:{N}D)?(?:T(?:{N}H)?(?:{N}M)?(?:{N}S)?)?)"
)
SECONDS = (7 * 86400, 365 * 86400, 30 * 86400, 86400, 3600, 60, 1)


def iso_duration_seconds(s: str) -> int:
    match = PATTERN.fullmatch(s)
    if match is None:
        raise ValueError(f"invalid duration: {s!r}")
    present = [(value, unit) for value, unit in zip(match.groups(), SECONDS) if value is not None]
    if not present:
        raise ValueError("no components")
    if "T" in s and s.index("T") == len(s) - 1:
        raise ValueError("T with no time components")
    if any(re.search(r"[.,]", value) for value, _ in present[:-1]):
        raise ValueError("only the last component may have a fraction")
    total = sum(Fraction(value.replace(",", ".")) * unit for value, unit in present)
    return int(total)
