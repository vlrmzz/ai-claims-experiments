import re

NUM = r"(?:0|[1-9][0-9]*)"
IDENT = r"[0-9A-Za-z-]+"
PRE_IDENT = rf"(?:{NUM}|[0-9]*[A-Za-z-][0-9A-Za-z-]*)"
SEMVER = re.compile(rf"({NUM})\.({NUM})\.({NUM})(?:-({PRE_IDENT}(?:\.{PRE_IDENT})*))?(?:\+{IDENT}(?:\.{IDENT})*)?")


def _key(version):
    match = SEMVER.fullmatch(version)
    if match is None:
        raise ValueError(f"invalid version: {version!r}")
    major, minor, patch, pre = match.groups()
    if pre is None:
        pre_key = (1,)
    else:
        pre_key = (0, tuple((0, int(p), "") if p.isdigit() else (1, 0, p) for p in pre.split(".")))
    return (int(major), int(minor), int(patch), pre_key)


def sort_versions(versions: list[str]) -> list[str]:
    keys = [_key(v) for v in versions]  # validates everything before sorting
    order = sorted(range(len(versions)), key=lambda i: keys[i])
    return [versions[i] for i in order]
