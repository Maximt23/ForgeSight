"""
Async SQLAlchemy session management.

Reads `DATABASE_URL` from environment. Defaults to a local Postgres for
docker-compose dev. Use the `get_session` dependency in FastAPI routes:

    from packages.db import get_session
    from sqlalchemy.ext.asyncio import AsyncSession
    from fastapi import Depends

    @app.get("/things")
    async def list_things(session: AsyncSession = Depends(get_session)):
        result = await session.execute(select(Thing))
        return result.scalars().all()

Copyright (c) 2024-2026 Walmart Inc. All rights reserved.
"""

from __future__ import annotations

import os
from functools import lru_cache
from typing import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine


@lru_cache(maxsize=1)
def _database_url() -> str:
    """Resolve the database URL once and cache it."""
    return os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://cadowl:cadowl@localhost:5432/cadowl",
    )


@lru_cache(maxsize=1)
def _create_engine() -> AsyncEngine:
    return create_async_engine(
        _database_url(),
        echo=os.getenv("SQL_ECHO", "false").lower() == "true",
        pool_pre_ping=True,
        pool_size=int(os.getenv("DB_POOL_SIZE", "5")),
        max_overflow=int(os.getenv("DB_MAX_OVERFLOW", "10")),
        pool_recycle=int(os.getenv("DB_POOL_RECYCLE_SECONDS", "3600")),
    )


# Lazy module-level handles. Tests can override DATABASE_URL before first use.
engine: AsyncEngine = _create_engine()
async_session_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency that yields a per-request async session."""
    async with async_session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        else:
            # Commit only if the route handler didn't raise. Routes can still
            # call session.flush() / session.commit() explicitly when needed.
            await session.commit()
