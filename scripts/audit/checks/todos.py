"""
TODO / FIXME / XXX / HACK tracker.

Scans source + docs for action-item markers. Doesn't fail the build,
just keeps an inventory so they don't accumulate forever.

Copyright (c) 2024-2026 Walmart Inc. All rights reserved.
"""

from __future__ import annotations

import re
import time
from pathlib import Path

from ..types import REPO_ROOT, CheckResult, Finding, Severity

_MARKER_PATTERN = re.compile(r"\b(TODO|FIXME|XXX|HACK|BUG)\b[:\s](.*)$", re.IGNORECASE)
_SCAN_DIRS = ("apps", "packages", "scripts", "tests", "docs", "infra")
_SKIP_PARTS = {"__pycache__", "versions", ".venv", "node_modules"}
_SCAN_EXTENSIONS = {".py", ".md", ".yaml", ".yml", ".sh", ".ini"}

# Markers older than this should auto-escalate to ERROR
_STALE_AGE_DAYS = 90


def _is_skippable(path: Path) -> bool:
    return any(part in _SKIP_PARTS for part in path.parts)


def run() -> CheckResult:
    start = time.perf_counter()
    result = CheckResult(check="todos")

    files: list[Path] = []
    for d in _SCAN_DIRS:
        root = REPO_ROOT / d
        if not root.exists():
            continue
        for p in root.rglob("*"):
            if p.is_file() and p.suffix in _SCAN_EXTENSIONS and not _is_skippable(p):
                files.append(p)

    result.items_scanned = len(files)
    marker_counts: dict[str, int] = {"TODO": 0, "FIXME": 0, "XXX": 0, "HACK": 0, "BUG": 0}

    for path in files:
        try:
            for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                match = _MARKER_PATTERN.search(line)
                if not match:
                    continue
                marker = match.group(1).upper()
                marker_counts[marker] = marker_counts.get(marker, 0) + 1
                msg = match.group(2).strip()

                # FIXME / BUG / HACK = higher severity; TODO = info
                if marker in {"FIXME", "BUG"}:
                    severity = Severity.WARNING
                elif marker == "HACK":
                    severity = Severity.WARNING
                else:
                    severity = Severity.INFO

                result.findings.append(
                    Finding(
                        check="todos",
                        severity=severity,
                        title=f"{marker}: {msg[:80]}{'...' if len(msg) > 80 else ''}",
                        detail=line.strip(),
                        file=str(path.relative_to(REPO_ROOT)),
                        line=lineno,
                        metadata={"marker": marker},
                    )
                )
        except (OSError, UnicodeDecodeError):
            continue

    # Summary finding
    total = sum(marker_counts.values())
    if total > 0:
        summary = ", ".join(f"{k}={v}" for k, v in marker_counts.items() if v > 0)
        result.findings.insert(
            0,
            Finding(
                check="todos",
                severity=Severity.INFO,
                title=f"Marker inventory: {total} markers found",
                detail=summary,
                metadata=marker_counts,
            ),
        )

    result.duration_ms = (time.perf_counter() - start) * 1000
    return result
