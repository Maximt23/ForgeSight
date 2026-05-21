"""
Dependency check.

Compares `requirements.txt` (declared deps) against actually imported
packages in source code. Catches:
  - Declared deps not imported anywhere (bloat)
  - Imported packages not declared (missing — will break in fresh env)

Copyright (c) 2024-2026 Walmart Inc. All rights reserved.
"""

from __future__ import annotations

import ast
import re
import sys
import time
from pathlib import Path

from ..types import REPO_ROOT, CheckResult, Finding, Severity

_SCAN_DIRS = ("apps", "packages", "scripts")
_SKIP_PARTS = {"__pycache__", "versions", ".venv"}

# stdlib + first-party names we never expect to see in requirements.txt
_STDLIB = set(sys.stdlib_module_names) | {
    # First-party top-level packages (legacy + new namespaces)
    "apps", "packages", "scripts", "tests",
    "app",         # legacy entrypoint
    "cadowl",      # legacy package (CadOwl name)
    "forgesight",  # new package (post-rebrand)
}

# Map import name → pip package name when they differ
_IMPORT_TO_PIP = {
    "jose": "python-jose",
    "dotenv": "python-dotenv",
    "yaml": "PyYAML",
    "sklearn": "scikit-learn",
    "PIL": "pillow",
    "cv2": "opencv-python",
    "pkg_resources": "setuptools",
    "fitz": "PyMuPDF",
    "psycopg": "psycopg",
}


def _parse_requirements(path: Path) -> set[str]:
    """Extract canonical pip package names from requirements.txt."""
    pkgs = set()
    if not path.exists():
        return pkgs
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        # strip version specifier and extras
        match = re.match(r"^([A-Za-z0-9_.\-]+)", line)
        if match:
            pkgs.add(match.group(1).lower().replace("_", "-"))
    return pkgs


def _collect_imports(root: Path) -> set[str]:
    """Walk every .py file under root and collect top-level imports."""
    imports: set[str] = set()
    for d in _SCAN_DIRS:
        scan_root = root / d
        if not scan_root.exists():
            continue
        for p in scan_root.rglob("*.py"):
            if any(part in _SKIP_PARTS for part in p.parts):
                continue
            try:
                tree = ast.parse(p.read_text(encoding="utf-8"))
            except (SyntaxError, OSError, UnicodeDecodeError):
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.add(alias.name.split(".")[0])
                elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                    imports.add(node.module.split(".")[0])
    return imports


def run() -> CheckResult:
    start = time.perf_counter()
    result = CheckResult(check="deps")

    declared = _parse_requirements(REPO_ROOT / "requirements.txt")
    imported = _collect_imports(REPO_ROOT)

    # Filter stdlib + first-party from imports
    imported_third_party = {i for i in imported if i not in _STDLIB and not i.startswith("_")}

    # Map import name → pip name
    needed_pip = {_IMPORT_TO_PIP.get(i, i).lower().replace("_", "-") for i in imported_third_party}

    # Packages that come transitively with other declared deps — OK to import
    # without declaring directly. (We declare fastapi, which pulls in starlette
    # and anyio; uvicorn[standard] pulls in httptools etc.)
    _TRANSITIVE_OK = {
        "starlette",  # pulled in by fastapi
        "anyio",      # pulled in by fastapi/starlette
        "sniffio",    # pulled in by anyio
        "h11",        # pulled in by uvicorn/httpx
        "idna",       # pulled in by httpx/email-validator
        "certifi",    # pulled in by httpx
        "charset-normalizer",  # pulled in by requests/httpx
        "typing-extensions",   # pulled in by pydantic
        "annotated-types",     # pulled in by pydantic
        "pydantic-core",       # pulled in by pydantic
    }

    result.items_scanned = len(declared) + len(imported)

    # 1. Missing: imported but not declared (and not transitively OK)
    missing = needed_pip - declared - _TRANSITIVE_OK
    for pkg in sorted(missing):
        result.findings.append(
            Finding(
                check="deps",
                severity=Severity.ERROR,
                title=f"Missing requirement: {pkg}",
                detail=f"The package `{pkg}` is imported in source but not listed in requirements.txt",
                suggestion=f"Add `{pkg}` to requirements.txt with a pinned version.",
                metadata={"package": pkg},
            )
        )

    # 2. Unused: declared but not imported
    # Filter known meta-packages and dev tools we don't directly import
    known_indirect = {
        "psycopg",  # used via SQLAlchemy URL string
        "uvicorn",  # entrypoint
        "asyncpg",  # used via SQLAlchemy URL string
        "alembic",  # CLI tool
        "pytest",  # test runner
        "pytest-asyncio",
        "pytest-cov",
        "ruff",
        "mypy",
        "redis",  # used by arq
        "pillow",
        "aiosqlite",
        "loguru",  # imported in worker setup
        "python-multipart",  # form parsing
        "click",  # CLI deps
        "tzdata",
        "starlette",  # bundled with FastAPI
        "greenlet",   # SQLAlchemy async
        "jinja2",     # FastAPI templates
        "anyio",      # async runtime
        "httpx",      # often used via FastAPI TestClient
    }
    unused = declared - needed_pip - known_indirect
    for pkg in sorted(unused):
        result.findings.append(
            Finding(
                check="deps",
                severity=Severity.INFO,
                title=f"Possibly unused requirement: {pkg}",
                detail=f"`{pkg}` is declared in requirements.txt but no source file imports it directly.",
                suggestion="If truly unused, remove. If used indirectly (transitive runtime dep), add it to the known_indirect allowlist.",
                metadata={"package": pkg},
            )
        )

    result.duration_ms = (time.perf_counter() - start) * 1000
    return result
