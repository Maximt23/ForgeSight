"""
Alembic migration drift check.

Runs `alembic check` against an in-memory SQLite database to detect
whether the SQLAlchemy models have changed in ways that need a new
migration. Catches "model added but no migration generated" hallucinations.

Copyright (c) 2024-2026 Walmart Inc. All rights reserved.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
import tempfile
from pathlib import Path

from ..types import REPO_ROOT, CheckResult, Finding, Severity


def run() -> CheckResult:
    start = time.perf_counter()
    result = CheckResult(check="migrations")

    alembic_ini = REPO_ROOT / "alembic.ini"
    if not alembic_ini.exists():
        result.findings.append(
            Finding(
                check="migrations",
                severity=Severity.WARNING,
                title="No alembic.ini found",
                detail="Database migrations not configured.",
                suggestion="Run `alembic init` or skip if not using SQL persistence.",
            )
        )
        result.duration_ms = (time.perf_counter() - start) * 1000
        return result

    # Use a temp SQLite DB so we don't touch the real DATABASE_URL
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "audit.db"
        env = os.environ.copy()
        env["DATABASE_URL"] = f"sqlite+aiosqlite:///{db_path}"

        # Step 1: apply current migrations to a clean DB
        upgrade = subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            cwd=REPO_ROOT,
            env=env,
            capture_output=True,
            text=True,
        )
        result.items_scanned += 1
        if upgrade.returncode != 0:
            result.findings.append(
                Finding(
                    check="migrations",
                    severity=Severity.ERROR,
                    title="Migrations fail to apply",
                    detail=upgrade.stderr.strip()[-500:],
                    suggestion="Fix the failing migration before merging.",
                )
            )
            result.duration_ms = (time.perf_counter() - start) * 1000
            return result

        # Step 2: ask Alembic if the models have diverged from the DB
        check = subprocess.run(
            [sys.executable, "-m", "alembic", "check"],
            cwd=REPO_ROOT,
            env=env,
            capture_output=True,
            text=True,
        )
        result.items_scanned += 1
        if check.returncode != 0:
            # Alembic exit code 1 = drift detected
            result.findings.append(
                Finding(
                    check="migrations",
                    severity=Severity.ERROR,
                    title="Model/migration drift detected",
                    detail=(check.stdout + check.stderr).strip()[-1000:],
                    suggestion="Run `alembic revision --autogenerate -m 'describe change'` and review the generated migration.",
                )
            )

    result.duration_ms = (time.perf_counter() - start) * 1000
    return result
