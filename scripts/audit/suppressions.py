"""
Suppression loader for the audit system.

Lets us mark known-and-tracked findings so they don't keep failing CI
while a real ticket is pending. Suppressions MUST have:
  - A reason (what's actually going on)
  - An expires date (so suppressions don't become permanent lies)

When an endpoint is suppressed, its finding is downgraded from
ERROR → INFO and tagged with the reason + ticket. When the suppression
expires, the finding upgrades back to ERROR (with a note that the
suppression is stale).

Copyright (c) 2024-2026 Walmart Inc. All rights reserved.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Optional

from .types import REPO_ROOT


@dataclass(slots=True)
class Suppression:
    key: str
    reason: str
    ticket: Optional[str]
    expires: date

    @property
    def expired(self) -> bool:
        return date.today() > self.expires


def load_suppressions() -> dict[str, dict[str, Suppression]]:
    """Load suppressions from scripts/audit/suppressions.json.

    Returns: {check_name: {key: Suppression}}
    """
    path = REPO_ROOT / "scripts" / "audit" / "suppressions.json"
    if not path.exists():
        return {}

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}

    result: dict[str, dict[str, Suppression]] = {}
    for check_name, entries in raw.items():
        if check_name.startswith("_") or not isinstance(entries, list):
            continue
        result[check_name] = {}
        for entry in entries:
            # Each check decides what field is the "key"
            key_field = {
                "endpoints": "endpoint",
                "imports": "module",
                "deps": "package",
                "schemas": "entity",
            }.get(check_name, "key")

            key = entry.get(key_field)
            if not key:
                continue
            try:
                expires = date.fromisoformat(entry["expires"])
            except (KeyError, ValueError):
                continue
            result[check_name][key] = Suppression(
                key=key,
                reason=entry.get("reason", "(no reason given)"),
                ticket=entry.get("ticket"),
                expires=expires,
            )
    return result
