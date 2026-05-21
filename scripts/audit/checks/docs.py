"""
Documentation reality check.

Walks every .md file and verifies:
  - File references like `apps/api/foo.py` actually exist
  - Relative markdown links `[X](./Y.md)` resolve

Catches docs that drift after code moves or files are deleted.

Copyright (c) 2024-2026 Walmart Inc. All rights reserved.
"""

from __future__ import annotations

import re
import time
from pathlib import Path
from urllib.parse import urlparse

from ..types import REPO_ROOT, CheckResult, Finding, Severity

# Match `[text](path)` markdown links, excluding URLs
_MD_LINK = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")

# Match inline code mentioning file paths like `apps/api/foo.py`
_FILE_PATH = re.compile(r"`([a-zA-Z0-9_./\-]+\.(?:py|md|yaml|yml|json|ini|toml))`")

_SCAN_DIRS = ("", "docs", "apps", "packages", "infra", "scripts")
_SKIP_PARTS = {"__pycache__", "versions", ".venv", "node_modules"}


def _is_external(target: str) -> bool:
    parsed = urlparse(target)
    return bool(parsed.scheme) and parsed.scheme not in {"", "file"}


def run() -> CheckResult:
    start = time.perf_counter()
    result = CheckResult(check="docs")

    md_files: list[Path] = []
    for d in _SCAN_DIRS:
        root = REPO_ROOT / d if d else REPO_ROOT
        if not root.exists():
            continue
        for p in root.rglob("*.md") if d else root.glob("*.md"):
            if not any(part in _SKIP_PARTS for part in p.parts):
                md_files.append(p)

    result.items_scanned = len(md_files)

    for md in md_files:
        try:
            content = md.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue

        # Check markdown links
        for lineno, line in enumerate(content.splitlines(), 1):
            for match in _MD_LINK.finditer(line):
                target = match.group(2).split("#")[0].strip()  # strip anchor
                if not target or _is_external(target):
                    continue

                # Resolve relative to the md file's directory
                candidate = (md.parent / target).resolve()
                if not candidate.exists():
                    # Try absolute from repo root
                    abs_candidate = (REPO_ROOT / target.lstrip("/")).resolve()
                    if not abs_candidate.exists():
                        result.findings.append(
                            Finding(
                                check="docs",
                                severity=Severity.WARNING,
                                title=f"Broken link in {md.name}: {target}",
                                detail=f"Linked path does not resolve to an existing file.",
                                file=str(md.relative_to(REPO_ROOT)),
                                line=lineno,
                                suggestion="Update the link or remove it.",
                                metadata={"target": target},
                            )
                        )

            # Check file path mentions in backticks
            for match in _FILE_PATH.finditer(line):
                path_str = match.group(1)
                if path_str.startswith("http") or "/" not in path_str:
                    continue
                candidate = (REPO_ROOT / path_str).resolve()
                if not candidate.exists():
                    # Try resolving relative to docs dir
                    alt = (md.parent / path_str).resolve()
                    if not alt.exists():
                        result.findings.append(
                            Finding(
                                check="docs",
                                severity=Severity.INFO,
                                title=f"Referenced file not found: {path_str}",
                                detail=f"Docs mention `{path_str}` but no such file in the repo.",
                                file=str(md.relative_to(REPO_ROOT)),
                                line=lineno,
                                suggestion="Update the docs to reflect the actual file location.",
                                metadata={"referenced_file": path_str},
                            )
                        )

    result.duration_ms = (time.perf_counter() - start) * 1000
    return result
