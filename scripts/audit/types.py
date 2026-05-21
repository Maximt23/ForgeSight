"""
Shared types for audit checks.

Each check returns a list of `Finding`s. A run collects all findings,
groups by severity, and decides exit code (error → 1, warning → 0).

Copyright (c) 2024-2026 Walmart Inc. All rights reserved.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Optional


# Repository root — resolved once based on this file's location.
REPO_ROOT: Path = Path(__file__).resolve().parents[2]


class Severity(str, Enum):
    """Severity ranking used to drive exit code + report grouping."""

    INFO = "info"          # informational only, never fails CI
    WARNING = "warning"    # something to fix soon, doesn't fail CI
    ERROR = "error"        # real bug / drift, fails CI
    CRITICAL = "critical"  # production-blocking, fails CI


@dataclass(slots=True)
class Finding:
    """A single audit finding."""

    check: str                       # check name (e.g., "endpoints")
    severity: Severity
    title: str                       # short headline
    detail: str                      # longer explanation
    file: Optional[str] = None       # file path (relative to repo root) when applicable
    line: Optional[int] = None       # line number when applicable
    suggestion: Optional[str] = None # what to do about it
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "check": self.check,
            "severity": self.severity.value,
            "title": self.title,
            "detail": self.detail,
            "file": self.file,
            "line": self.line,
            "suggestion": self.suggestion,
            "metadata": self.metadata,
        }


@dataclass(slots=True)
class CheckResult:
    """One check's complete output."""

    check: str
    findings: list[Finding] = field(default_factory=list)
    items_scanned: int = 0
    duration_ms: float = 0.0
    error: Optional[str] = None  # set if the check itself crashed

    @property
    def passed(self) -> bool:
        return self.error is None and not any(
            f.severity in (Severity.ERROR, Severity.CRITICAL) for f in self.findings
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "check": self.check,
            "passed": self.passed,
            "items_scanned": self.items_scanned,
            "duration_ms": self.duration_ms,
            "error": self.error,
            "findings": [f.to_dict() for f in self.findings],
            "by_severity": {
                sev.value: sum(1 for f in self.findings if f.severity == sev)
                for sev in Severity
            },
        }
