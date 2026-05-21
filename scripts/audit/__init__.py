"""
CadOwl / ForgeSight ongoing audit system.

Runs a battery of reality-checks against the codebase to catch:
- Hallucinated endpoints in docs that don't exist in code
- Hallucinated modules referenced but missing
- Schema drift (Pydantic ↔ SQLAlchemy ↔ JSON schemas)
- Untested code paths
- Files exceeding sanity limits (600 LoC per CLAUDE.md)
- Orphan files nobody imports
- Dependencies declared but unused (and vice versa)
- Pending Alembic migrations
- Stale TODO/FIXME markers
- Broken markdown links

Run:
    python -m scripts.audit                  # full audit, fail on errors
    python -m scripts.audit --html report.html
    python -m scripts.audit --json out.json
    python -m scripts.audit --check endpoints  # one check only

CI integration: `.github/workflows/audit.yml`

Copyright (c) 2024-2026 Walmart Inc. All rights reserved.
"""

__version__ = "1.0.0"
