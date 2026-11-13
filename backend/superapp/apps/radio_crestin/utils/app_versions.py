"""App version strings ('1.6.2', 'v1.6', '1.6.2+56') as comparable values."""
import re
from typing import Optional

VERSION_CODE_PARTS = 4
VERSION_CODE_BASE = 10_000


def parse_version(version: str) -> Optional[tuple]:
    """'1.6.2', 'v1.6', '1.6.2+56' or '1.6.2-beta' -> (1, 6, 2); None when unparseable."""
    match = re.match(r'^\s*v?(\d+(?:\.\d+)*)', version or '')
    if not match:
        return None
    parts = [int(part) for part in match.group(1).split('.')]
    return tuple(parts + [0] * (3 - len(parts)))


def version_code(version: str) -> Optional[int]:
    """'1.6.2' -> 1_0006_0002_0000: one integer that sorts like the version, so the database can compare it.

    Same order as comparing parse_version tuples for up to 4 parts below 10,000 each (larger
    parts are capped); None when unparseable.
    """
    parts = parse_version(version)
    if parts is None:
        return None
    parts = (list(parts) + [0] * VERSION_CODE_PARTS)[:VERSION_CODE_PARTS]
    code = 0
    for part in parts:
        code = code * VERSION_CODE_BASE + min(part, VERSION_CODE_BASE - 1)
    return code
