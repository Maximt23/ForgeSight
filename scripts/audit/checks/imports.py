"""
Import resolution check.

Walks every .py file under apps/, packages/, scripts/, tests/ and tries
to import it (in isolation). Catches:
  - Modules that reference missing dependencies
  - Modules with circular imports
  - Modules with syntax errors
  - Modules that reference missing sibling modules

This is the broadest "does the code even load" check.

Copyright (c) 2024-2026 Walmart Inc. All rights reserved.
"""

from __future__ import annotations

import ast
import importlib
import os
import sys
import time
from pathlib import Path

from ..types import REPO_ROOT, CheckResult, Finding, Severity

# Directories whose .py files we attempt to import
_SCAN_DIRS = ("apps", "packages", "scripts", "tests")

# Skip pyc/cache/migration dirs
_SKIP_PARTS = {"__pycache__", "versions", ".pytest_cache", ".venv", ".ruff_cache"}


def _is_skippable(path: Path) -> bool:
    return any(part in _SKIP_PARTS for part in path.parts)


def _path_to_module(path: Path) -> str:
    """Convert a file path to a dotted module name."""
    rel = path.relative_to(REPO_ROOT).with_suffix("")
    parts = list(rel.parts)
    if parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)


def _walk_py_files() -> list[Path]:
    files: list[Path] = []
    for d in _SCAN_DIRS:
        root = REPO_ROOT / d
        if not root.exists():
            continue
        for p in root.rglob("*.py"):
            if not _is_skippable(p):
                files.append(p)
    return files


def _try_parse(path: Path) -> str | None:
    """Return error message if file has a syntax error, else None."""
    try:
        ast.parse(path.read_text(encoding="utf-8"))
        return None
    except SyntaxError as exc:
        return f"{exc.msg} at line {exc.lineno}"
    except (OSError, UnicodeDecodeError) as exc:
        return f"could not read file: {exc}"


def _try_import(module_name: str) -> str | None:
    """Return error message if import fails, else None."""
    try:
        # Avoid re-importing already-loaded modules (faster, less noise)
        if module_name in sys.modules:
            return None
        importlib.import_module(module_name)
        return None
    except Exception as exc:  # noqa: BLE001 — really do want all of them
        return f"{type(exc).__name__}: {exc}"


def run() -> CheckResult:
    start = time.perf_counter()
    result = CheckResult(check="imports")

    # Make sure dev mode is on so auth-protected imports work
    os.environ.setdefault("CADOWL_DEV_MODE", "true")

    # Ensure repo root is on sys.path
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))

    files = _walk_py_files()
    result.items_scanned = len(files)

    for path in files:
        # 1. Syntax check first (cheaper than import)
        syntax_error = _try_parse(path)
        if syntax_error:
            result.findings.append(
                Finding(
                    check="imports",
                    severity=Severity.CRITICAL,
                    title=f"Syntax error in {path.name}",
                    detail=syntax_error,
                    file=str(path.relative_to(REPO_ROOT)),
                    suggestion="Fix the syntax error — file cannot be executed.",
                )
            )
            continue

        # 2. Import attempt (skip tests — they import test fixtures we may
        #    not want to actually run)
        if "tests" in path.parts:
            continue
        # Skip __main__ files and Alembic env.py (uses runtime globals)
        if path.name in {"__main__.py", "env.py"}:
            continue

        module_name = _path_to_module(path)
        if not module_name:
            continue

        import_error = _try_import(module_name)
        if import_error:
            # Some optional integrations are OK to fail at import time
            optional_prefixes = ("packages.integrations.",)
            severity = Severity.WARNING if module_name.startswith(optional_prefixes) and "ModuleNotFoundError" in import_error else Severity.ERROR
            result.findings.append(
                Finding(
                    check="imports",
                    severity=severity,
                    title=f"Import failed: {module_name}",
                    detail=import_error,
                    file=str(path.relative_to(REPO_ROOT)),
                    suggestion="Fix the import or add the missing dependency to requirements.txt.",
                    metadata={"module": module_name},
                )
            )

    result.duration_ms = (time.perf_counter() - start) * 1000
    return result
