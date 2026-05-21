"""
Orphan file check.

Finds Python files in apps/ and packages/ that are NOT imported by
anything else (and aren't entry points). These are often dead code
left over from refactors — a common source of hallucination ("the docs
say to use this!" but nobody actually does).

Copyright (c) 2024-2026 Walmart Inc. All rights reserved.
"""

from __future__ import annotations

import ast
import time
from pathlib import Path

from ..types import REPO_ROOT, CheckResult, Finding, Severity

_SCAN_DIRS = ("apps", "packages")
_SKIP_PARTS = {"__pycache__", "versions", ".venv"}

# Files that are entry points (no one imports them, but they're not orphans)
_ENTRY_POINTS = {
    "__init__.py",
    "__main__.py",
    "main.py",       # app entrypoints
    "conftest.py",   # pytest auto-discovery
    "env.py",        # Alembic
    "settings.py",   # often loaded via env, not import
}


def _module_name(path: Path) -> str:
    return path.stem


def _is_skippable(path: Path) -> bool:
    return any(part in _SKIP_PARTS for part in path.parts)


def run() -> CheckResult:
    start = time.perf_counter()
    result = CheckResult(check="orphans")

    # Collect candidate modules
    candidates: dict[str, Path] = {}
    for d in _SCAN_DIRS:
        root = REPO_ROOT / d
        if not root.exists():
            continue
        for p in root.rglob("*.py"):
            if _is_skippable(p) or p.name in _ENTRY_POINTS:
                continue
            candidates[_module_name(p)] = p

    # Walk ALL python files (including tests, scripts) and collect imports
    all_imports: set[str] = set()
    for root_dir in ("apps", "packages", "scripts", "tests"):
        root = REPO_ROOT / root_dir
        if not root.exists():
            continue
        for p in root.rglob("*.py"):
            if _is_skippable(p):
                continue
            try:
                tree = ast.parse(p.read_text(encoding="utf-8"))
            except (SyntaxError, OSError, UnicodeDecodeError):
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        all_imports.add(alias.name.split(".")[-1])
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        all_imports.add(node.module.split(".")[-1])
                    for alias in node.names:
                        all_imports.add(alias.name)

    result.items_scanned = len(candidates)

    for name, path in candidates.items():
        if name not in all_imports:
            result.findings.append(
                Finding(
                    check="orphans",
                    severity=Severity.INFO,
                    title=f"Possibly orphaned module: {name}",
                    detail=f"{path.relative_to(REPO_ROOT)} is not imported anywhere in the repo.",
                    file=str(path.relative_to(REPO_ROOT)),
                    suggestion="If truly unused, delete. If it's an entry point, add to _ENTRY_POINTS in the orphans check.",
                    metadata={"module": name},
                )
            )

    result.duration_ms = (time.perf_counter() - start) * 1000
    return result
