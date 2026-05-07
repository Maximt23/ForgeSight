"""Domain spatial signal helpers (department + aisle intelligence)."""

from __future__ import annotations

import re
from typing import Dict, Optional

DEFAULT_DEPARTMENT_CODE_MAP: Dict[str, str] = {
    "A": "Groceries",
    "Y": "Garden Center",
    "Z": "Front End",
}

DEPARTMENT_SYSTEMS = {"Fire Alarm", "Video Surveillance"}
AISLE_SYSTEMS = {"Fire Alarm", "Video Surveillance"}


def extract_department_code(
    layer: str,
    block_name: str,
    raw_name: str,
    attributes: Dict[str, str],
    system_guess: str,
    department_map: Dict[str, str],
) -> Optional[str]:
    """Extract department code token (A/Y/Z) for scoped systems only."""
    if system_guess not in DEPARTMENT_SYSTEMS:
        return None

    candidates = [layer, block_name, raw_name]
    candidates.extend(attributes.values())
    joined = " ".join(candidates).upper()

    for code in department_map:
        if re.search(rf"(^|[^A-Z0-9]){code}([^A-Z0-9]|$)", joined):
            return code
    return None


def department_name(code: Optional[str], department_map: Dict[str, str]) -> Optional[str]:
    if not code:
        return None
    return department_map.get(code.upper())


def extract_aisle_number(
    layer: str,
    block_name: str,
    raw_name: str,
    attributes: Dict[str, str],
    system_guess: str,
) -> Optional[int]:
    """Extract aisle number from CAD tokens.

    Heuristics:
    - Prefer explicit AISLE attribute tags
    - Then parse values containing 'AISLE xx'/'AISL xx'
    """
    if system_guess not in AISLE_SYSTEMS:
        return None

    explicit_tags = ["AISLE", "AISLE_NO", "AISLE#", "AISLENO", "A_NO", "AISL"]
    for tag in explicit_tags:
        value = attributes.get(tag)
        if not value:
            continue
        m = re.search(r"(\d{1,3})", value)
        if m:
            return int(m.group(1))

    haystack = " ".join([layer, block_name, raw_name, *attributes.values()]).upper()
    m = re.search(r"(?:AISLE|AISL)\s*[-#:]?\s*(\d{1,3})\b", haystack)
    if m:
        return int(m.group(1))

    return None


def aisle_direction_hint(aisle_number: Optional[int], first_aisle_direction: str = "RTL") -> Optional[str]:
    """Serpentine travel direction hint from aisle number parity.

    If first aisle is RTL, then odd aisles => RTL, even => LTR.
    """
    if aisle_number is None:
        return None

    first = first_aisle_direction.upper().strip()
    if first not in {"RTL", "LTR"}:
        first = "RTL"

    is_odd = aisle_number % 2 == 1
    if first == "RTL":
        return "RTL" if is_odd else "LTR"
    return "LTR" if is_odd else "RTL"
