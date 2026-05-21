"""
Database layer — SQLAlchemy async + Alembic.

Currently the API uses an in-memory + JSON file store (`apps/api/store.py`).
Phase 1.1 migrates to PostgreSQL backed by SQLAlchemy 2.x async engine.

Layout:
- models.py    : ORM models mirroring `apps/api/schemas.py`
- session.py   : Async engine + sessionmaker + FastAPI dependency
- migrations/  : Alembic-managed schema migrations

Copyright (c) 2024-2026 Walmart Inc. All rights reserved.
"""

from .session import async_session_factory, engine, get_session

__all__ = ["async_session_factory", "engine", "get_session"]
