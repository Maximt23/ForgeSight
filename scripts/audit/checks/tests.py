"""
Test coverage gap check.

Lists every Python module under apps/ and packages/, then checks whether
there is at least one test file referencing it. Doesn't measure line
coverage (that's pytest-cov's job) — this is a much faster "is anything
testing this module at all?" sanity check.

Copyright (c) 2024-2026 Walmart Inc. All rights reserved.
"""

from __future__ import annotations

import time
from pathlib import Path

from ..types import REPO_ROOT, CheckResult, Finding, Severity

_SCAN_DIRS = ("apps", "packages")
_SKIP_PARTS = {"__pycache__", "versions", ".venv", "migrations"}

# Modules that don't need test coverage
_EXEMPT = {
    "__init__",
    "main",  # entrypoints
    "models",  # tested transitively via DB tests
    "schemas",  # tested transitively
    "settings",
}


def _module_name(path: Path) -> str:
    return path.stem


def _is_skippable(path: Path) -> bool:
    return any(part in _SKIP_PARTS for part in path.parts)


def run() -> CheckResult:
    start = time.perf_counter()
    result = CheckResult(check="tests")

    # Collect source modules
    source_modules: dict[str, Path] = {}
    for d in _SCAN_DIRS:
        root = REPO_ROOT / d
        if not root.exists():
            continue
        for p in root.rglob("*.py"):
            if _is_skippable(p) or _module_name(p) in _EXEMPT:
                continue
            source_modules[_module_name(p)] = p

    # Collect all test file contents (one big string for grep)
    test_root = REPO_ROOT / "tests"
    test_haystack = ""
    test_count = 0
    if test_root.exists():
        for p in test_root.rglob("test_*.py"):
            try:
                test_haystack += p.read_text(encoding="utf-8")
                test_count += 1
            except (OSError, UnicodeDecodeError):
                continue

    result.items_scanned = len(source_modules)

    for module_name, path in source_modules.items():
        # Did any test file reference this module?
        if module_name not in test_haystack and f".{module_name}" not in test_haystack:
            result.findings.append(
                Finding(
                    check="tests",
                    severity=Severity.WARNING,
                    title=f"No tests reference module: {module_name}",
                    detail=f"Source file {path.relative_to(REPO_ROOT)} is not mentioned in any test_*.py",
                    file=str(path.relative_to(REPO_ROOT)),
                    suggestion=f"Add tests/integration/test_{module_name}.py or unit tests as appropriate.",
                    metadata={"module": module_name, "test_files_searched": test_count},
                )
            )

    result.duration_ms = (time.perf_counter() - start) * 1000
    return result
