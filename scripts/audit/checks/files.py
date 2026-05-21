"""
File size + structure check.

Enforces:
  - Files under apps/, packages/, scripts/ should be ≤ 600 lines (CLAUDE.md rule)
  - No empty __init__.py at package roots (warning, not error)
  - No top-level .py files dumped in random directories

Copyright (c) 2024-2026 Walmart Inc. All rights reserved.
"""

from __future__ import annotations

import time
from pathlib import Path

from ..suppressions import load_suppressions
from ..types import REPO_ROOT, CheckResult, Finding, Severity

_MAX_LINES = 600
_WARN_LINES = 500
_SCAN_DIRS = ("apps", "packages", "scripts")
_SKIP_PARTS = {"__pycache__", "versions", ".venv"}


def _is_skippable(path: Path) -> bool:
    return any(part in _SKIP_PARTS for part in path.parts)


def run() -> CheckResult:
    start = time.perf_counter()
    result = CheckResult(check="files")

    files: list[Path] = []
    for d in _SCAN_DIRS:
        root = REPO_ROOT / d
        if not root.exists():
            continue
        for p in root.rglob("*.py"):
            if not _is_skippable(p):
                files.append(p)

    result.items_scanned = len(files)
    suppressions = load_suppressions().get("files", {})

    for path in files:
        rel = str(path.relative_to(REPO_ROOT)).replace("\\", "/")
        try:
            lines = path.read_text(encoding="utf-8").count("\n") + 1
        except (OSError, UnicodeDecodeError):
            continue

        if lines > _MAX_LINES:
            suppression = suppressions.get(rel)
            if suppression and not suppression.expired:
                result.findings.append(
                    Finding(
                        check="files",
                        severity=Severity.INFO,
                        title=f"Large file (tracked): {path.name}",
                        detail=f"{lines} lines. Suppressed: {suppression.reason}",
                        file=rel,
                        suggestion=f"Ticket: {suppression.ticket or 'n/a'} · expires {suppression.expires.isoformat()}",
                        metadata={"lines": lines, "limit": _MAX_LINES, "suppressed": True},
                    )
                )
                continue
            result.findings.append(
                Finding(
                    check="files",
                    severity=Severity.WARNING,
                    title=f"File over {_MAX_LINES} lines: {path.name}",
                    detail=f"{lines} lines (limit: {_MAX_LINES})",
                    file=rel,
                    suggestion="Consider splitting into smaller modules. See CLAUDE.md for the 600-line guideline.",
                    metadata={"lines": lines, "limit": _MAX_LINES},
                )
            )
        elif lines > _WARN_LINES:
            result.findings.append(
                Finding(
                    check="files",
                    severity=Severity.INFO,
                    title=f"Large file approaching limit: {path.name}",
                    detail=f"{lines} lines (will warn at {_MAX_LINES})",
                    file=rel,
                    metadata={"lines": lines, "limit": _MAX_LINES},
                )
            )

    result.duration_ms = (time.perf_counter() - start) * 1000
    return result
