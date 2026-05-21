"""
Migration runner — convenient wrapper around `alembic upgrade head`.

Use in container entrypoint, CI, or local dev:

    python -m scripts.migrate              # apply all pending migrations
    python -m scripts.migrate --check      # report current revision only
    python -m scripts.migrate --downgrade  # roll back one revision

Copyright (c) 2024-2026 Walmart Inc. All rights reserved.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def _alembic(args: list[str]) -> int:
    cmd = [sys.executable, "-m", "alembic", *args]
    return subprocess.call(cmd, cwd=Path(__file__).resolve().parent.parent)


def main() -> int:
    db_url = os.getenv("DATABASE_URL", "<not set — falling back to alembic.ini>")
    print(f"[migrate] Target database: {db_url}")

    if "--check" in sys.argv:
        return _alembic(["current"])

    if "--downgrade" in sys.argv:
        return _alembic(["downgrade", "-1"])

    return _alembic(["upgrade", "head"])


if __name__ == "__main__":
    raise SystemExit(main())
