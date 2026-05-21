"""
Schema drift check.

Three sources of truth exist for entities in this codebase:
  1. Pydantic schemas    (apps/api/schemas.py)
  2. SQLAlchemy models   (packages/db/models.py)
  3. JSON Schemas        (apps/api/schemas_json/)

When they drift, hallucinations follow. This check flags entity-level
mismatches (a Pydantic class with no SQLAlchemy table, etc.).

It does NOT check field-by-field equivalence (too noisy for an MVP),
just that each entity is consistently represented.

Copyright (c) 2024-2026 Walmart Inc. All rights reserved.
"""

from __future__ import annotations

import ast
import time
from pathlib import Path

from ..types import REPO_ROOT, CheckResult, Finding, Severity


def _class_names_in(path: Path, base_filter: tuple[str, ...] = ()) -> set[str]:
    """Return top-level class names defined in a file."""
    if not path.exists():
        return set()
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (SyntaxError, OSError, UnicodeDecodeError):
        return set()
    names: set[str] = set()
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.ClassDef):
            if not base_filter:
                names.add(node.name)
            else:
                # Check if any base matches the filter
                base_strs = [
                    base.id if isinstance(base, ast.Name) else
                    base.attr if isinstance(base, ast.Attribute) else ""
                    for base in node.bases
                ]
                if any(b in base_filter for b in base_strs):
                    names.add(node.name)
    return names


def _json_schemas() -> set[str]:
    """Return canonical entity names from JSON schemas (stem of file name)."""
    schemas_dir = REPO_ROOT / "apps" / "api" / "schemas_json"
    if not schemas_dir.exists():
        return set()
    return {
        p.stem.replace(".api.schema", "").lower()
        for p in schemas_dir.glob("*.json")
    }


# Entity names that exist intentionally in only one place
_PYDANTIC_ONLY = {
    "BaseEntity",  # base class, not an entity itself
    "ProjectCreate", "SiteCreate", "FloorCreate", "MapCreate", "DeviceCreate",
    "ZoneCreate", "CableCreate", "ImportBatchCreate", "ImportBatchCommitRequest",
    "ImportBatchCommitResponse", "RollbackRequest", "RollbackResult",
    "AsdpxBatchStageRequest", "AsdpxBatchStageResponse", "AsdpxPreviewRequest",
    "AsdpxPreviewResponse", "AsdpxDevicePreview",
    # Lifecycle helpers / DTOs (not persisted entities)
    "DesignCreate", "DesignFilter", "SiteFilter", "StatusChange",
    "DashboardStats", "DesignsByStatus", "SitesByType",
    # Import validation + re-upload + delete DTOs (request/response wrappers)
    "ImportBatchValidateResponse", "ImportBatchValidationIssue",
    "ImportDeleteCommitRequest", "ImportDeleteCommitResponse",
    "ImportDeletePreviewRequest", "ImportDeletePreviewResponse",
    "ImportReuploadCommitRequest", "ImportReuploadCommitResponse",
    "ImportReuploadPreviewRequest", "ImportReuploadPreviewResponse",
}

_SQL_ONLY = {
    "Base", "IdempotencyKey",  # internal infrastructure
    "Snapshot",  # state snapshot — internal, exposed via revision endpoints, not as a typed entity
}

# Entities that are intentionally in SQLAlchemy but use a different Pydantic name
_NAME_ALIASES = {
    "MapModel": "Map",  # Pydantic uses MapModel to avoid clash with builtin
    "SiteExtended": "SiteExtended",  # lifecycle Pydantic in apps/api/lifecycle.py
    "Design": "Design",
    "SandboxConfig": "SandboxConfig",
}


def run() -> CheckResult:
    start = time.perf_counter()
    result = CheckResult(check="schemas")

    pydantic_classes = _class_names_in(
        REPO_ROOT / "apps" / "api" / "schemas.py",
        base_filter=("BaseModel", "BaseEntity"),
    )
    # Lifecycle entities (SiteExtended, Design, SandboxConfig) live in lifecycle.py
    pydantic_classes |= _class_names_in(
        REPO_ROOT / "apps" / "api" / "lifecycle.py",
        base_filter=("BaseModel", "BaseEntity"),
    )
    sql_classes = _class_names_in(
        REPO_ROOT / "packages" / "db" / "models.py",
        base_filter=("Base",),
    )
    json_entities = _json_schemas()

    result.items_scanned = len(pydantic_classes) + len(sql_classes) + len(json_entities)

    # Normalize for comparison: lowercase, strip "Model" suffix
    def normalize(name: str) -> str:
        name = _NAME_ALIASES.get(name, name)
        return name.lower().replace("model", "")

    pydantic_norm = {normalize(c) for c in pydantic_classes if c not in _PYDANTIC_ONLY}
    sql_norm = {normalize(c) for c in sql_classes if c not in _SQL_ONLY}
    json_norm = {normalize(e) for e in json_entities}

    # 1. Pydantic entity with no SQLAlchemy model
    only_pydantic = pydantic_norm - sql_norm
    for name in sorted(only_pydantic):
        result.findings.append(
            Finding(
                check="schemas",
                severity=Severity.WARNING,
                title=f"Entity in Pydantic but missing SQLAlchemy model: {name}",
                detail=f"Pydantic class exists in apps/api/schemas.py but no matching table in packages/db/models.py",
                file="packages/db/models.py",
                suggestion=f"Add a SQLAlchemy model for {name} or document why it's API-only.",
                metadata={"entity": name},
            )
        )

    # 2. SQLAlchemy table with no Pydantic schema
    only_sql = sql_norm - pydantic_norm
    for name in sorted(only_sql):
        result.findings.append(
            Finding(
                check="schemas",
                severity=Severity.WARNING,
                title=f"Entity in SQLAlchemy but missing Pydantic schema: {name}",
                detail=f"Database table exists but no matching Pydantic API schema in apps/api/schemas.py",
                file="apps/api/schemas.py",
                suggestion=f"Add a Pydantic schema for {name} or document why it's storage-only.",
                metadata={"entity": name},
            )
        )

    # 3. JSON schema with no Pydantic equivalent
    only_json = json_norm - pydantic_norm
    for name in sorted(only_json):
        result.findings.append(
            Finding(
                check="schemas",
                severity=Severity.INFO,
                title=f"JSON schema with no Pydantic equivalent: {name}",
                detail=f"apps/api/schemas_json/{name}.api.schema.json exists but no Pydantic class",
                suggestion="Either add a Pydantic schema or remove the JSON file.",
                metadata={"entity": name},
            )
        )

    result.duration_ms = (time.perf_counter() - start) * 1000
    return result
