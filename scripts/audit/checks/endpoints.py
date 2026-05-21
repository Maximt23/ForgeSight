"""
Endpoint reality check.

Compares actual FastAPI routes (introspected at runtime) against:
  - Endpoints mentioned in docs/*.md
  - Endpoints listed in README.md

Catches:
  - Documented endpoints that don't exist  (hallucinated routes)
  - Real endpoints not documented anywhere (undocumented features)

Copyright (c) 2024-2026 Walmart Inc. All rights reserved.
"""

from __future__ import annotations

import os
import re
import time
from pathlib import Path

from ..suppressions import load_suppressions
from ..types import REPO_ROOT, CheckResult, Finding, Severity

# Strategy: only extract endpoint paths from contexts where they're
# clearly endpoints, not file paths or prose mentions. We look for:
#   1. Markdown code spans:   `/api/v1/foo` or `GET /api/v1/foo`
#   2. Markdown code fences:  ```...``` blocks
#   3. HTTP method prefixes:  `GET /api/...`, `POST /api/...`
_CODE_SPAN_PATTERN = re.compile(r"`([^`\n]+)`")
_CODE_FENCE_PATTERN = re.compile(r"```[\s\S]*?```", re.MULTILINE)
_PATH_IN_TEXT = re.compile(r"/api/[a-zA-Z0-9][a-zA-Z0-9/_\-{}.]+")
_METHOD_PATH = re.compile(r"\b(GET|POST|PUT|PATCH|DELETE)\s+(/api/[a-zA-Z0-9/_\-{}.]+)")


def _extract_endpoint_mentions(text: str) -> list[str]:
    """Pull /api/... paths from contexts where they're clearly endpoints.

    We use three signals (any one is enough):
      1. The path is inside a markdown code span (backticks)
      2. The path is inside a fenced code block
      3. The path is preceded by an HTTP method (GET, POST, etc.)

    Prose mentions like "see apps/api/main.py" do NOT produce false positives.
    """
    found: list[str] = []

    # 1. METHOD path (always counts)
    for match in _METHOD_PATH.finditer(text):
        found.append(match.group(2))

    # 2. Code spans — only count if the span IS the path (or method + path),
    #    not where /api/... appears inside a longer file path like `apps/api/foo.py`.
    for span_match in _CODE_SPAN_PATTERN.finditer(text):
        content = span_match.group(1).strip()
        # Strip leading method if present (`GET /api/v1/foo`)
        method_match = _METHOD_PATH.match(content)
        if method_match:
            found.append(method_match.group(2))
            continue
        # Otherwise the span must start with `/` to count as an endpoint
        if content.startswith("/"):
            for inner in _PATH_IN_TEXT.findall(content):
                if content == inner or content.startswith(inner):
                    found.append(inner)

    # 3. Fenced code blocks (think `curl http://localhost/api/...`)
    for fence in _CODE_FENCE_PATTERN.findall(text):
        for inner in _PATH_IN_TEXT.findall(fence):
            found.append(inner)

    return found


def _normalize(path: str) -> str:
    """Make documented and real endpoints comparable.

    Strips trailing slash, lowercases, removes the path param values (e.g.,
    `/api/v1/sites/{site_id}` matches `/api/v1/sites/abc-123`).
    """
    path = path.rstrip("/").lower()
    # Replace {anything} with a generic placeholder
    path = re.sub(r"\{[^}]+\}", "{}", path)
    return path


def _collect_real_routes() -> set[str]:
    """Import the FastAPI app and walk its routes."""
    # Make sure dev mode is on so the app loads without secrets
    os.environ.setdefault("CADOWL_DEV_MODE", "true")
    try:
        from apps.api.main import app
    except Exception as exc:  # noqa: BLE001 — broad on purpose
        raise RuntimeError(f"could not import app: {exc}") from exc

    routes: set[str] = set()
    for route in app.routes:
        path = getattr(route, "path", None)
        if path and path.startswith("/api"):
            routes.add(_normalize(path))
    return routes


def _collect_documented_routes(docs_root: Path) -> dict[str, list[tuple[Path, int]]]:
    """Scan all .md files for endpoint references in code contexts."""
    documented: dict[str, list[tuple[Path, int]]] = {}
    # Paths to ignore: file/module references and bare namespace prefixes
    skip_exact = {"/api/v1", "/api", "/api/exports", "/api/v1/exports"}
    skip_prefixes = ("apps/", "packages/", "scripts/")

    for md in docs_root.rglob("*.md"):
        try:
            content = md.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for lineno, line in enumerate(content.splitlines(), 1):
            for raw in _extract_endpoint_mentions(line):
                # Filter file-path mentions like `apps/api/...`
                if any(raw.startswith(p) or f" {p}" in raw for p in skip_prefixes):
                    continue
                key = _normalize(raw)
                if key in skip_exact:
                    continue
                if key.endswith((".py", ".md", ".json", ".yaml")):
                    continue
                # An endpoint should have at least 2 segments after /api/
                segments = [s for s in key.split("/") if s]
                if len(segments) < 2:
                    continue
                documented.setdefault(key, []).append((md, lineno))
    return documented


def run() -> CheckResult:
    start = time.perf_counter()
    result = CheckResult(check="endpoints")

    try:
        real = _collect_real_routes()
    except Exception as exc:  # noqa: BLE001
        result.error = str(exc)
        result.duration_ms = (time.perf_counter() - start) * 1000
        return result

    documented = _collect_documented_routes(REPO_ROOT)
    suppressions = load_suppressions().get("endpoints", {})
    result.items_scanned = len(real) + len(documented)

    # 1. Hallucinated endpoints (in docs but not in code)
    for doc_route, locations in documented.items():
        if doc_route in real:
            continue

        suppression = suppressions.get(doc_route)
        if suppression and not suppression.expired:
            # Tracked-and-suppressed: report as INFO with the rationale
            path, lineno = locations[0]
            result.findings.append(
                Finding(
                    check="endpoints",
                    severity=Severity.INFO,
                    title=f"Documented endpoint (tracked): {doc_route}",
                    detail=f"Suppressed: {suppression.reason}",
                    file=str(path.relative_to(REPO_ROOT)),
                    line=lineno,
                    suggestion=f"Ticket: {suppression.ticket or 'n/a'} · expires {suppression.expires.isoformat()}",
                    metadata={"endpoint": doc_route, "suppressed": True},
                )
            )
            continue

        # Real hallucination — escalate. If suppression is expired, note it.
        detail = f"Documented in {locations[0][0].relative_to(REPO_ROOT)}:{locations[0][1]} but no such route in the running app."
        if suppression and suppression.expired:
            detail += f" Suppression EXPIRED on {suppression.expires.isoformat()} — either ship the endpoint or update the docs."

        result.findings.append(
            Finding(
                check="endpoints",
                severity=Severity.ERROR,
                title=f"Hallucinated endpoint: {doc_route}",
                detail=detail,
                file=str(locations[0][0].relative_to(REPO_ROOT)),
                line=locations[0][1],
                suggestion="Either implement the endpoint, remove/update the doc, or add a tracked suppression with a ticket and expiry to scripts/audit/suppressions.json.",
                metadata={"endpoint": doc_route},
            )
        )

    # 2. Undocumented endpoints (in code but not in any doc)
    health_like = {"/api/v1/health", "/metrics", "/docs", "/openapi.json", "/redoc"}
    for real_route in real:
        if real_route in documented or real_route in health_like:
            continue
        result.findings.append(
            Finding(
                check="endpoints",
                severity=Severity.WARNING,
                title=f"Undocumented endpoint: {real_route}",
                detail="Route exists in code but is not mentioned in any .md file under the repo.",
                suggestion="Add the endpoint to docs/API.md or the relevant subsystem doc.",
                metadata={"endpoint": real_route},
            )
        )

    result.duration_ms = (time.perf_counter() - start) * 1000
    return result
