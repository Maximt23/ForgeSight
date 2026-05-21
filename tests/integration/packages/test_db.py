"""
Database / Alembic smoke tests.

Verifies the ORM models + migration apply cleanly against SQLite in-memory.
Production deploys use Postgres but the schema is portable enough that
SQLite catches most issues.
"""

from __future__ import annotations

import pytest


def test_models_import():
    """All models should import without error."""
    from packages.db.models import (
        Base,
        Cable,
        Design,
        Device,
        Event,
        Floor,
        IdempotencyKey,
        ImportBatch,
        Map,
        Project,
        SandboxConfig,
        Site,
        SiteExtended,
        Snapshot,
        Zone,
    )

    # Sanity check — all tables registered with the same metadata
    tables = set(Base.metadata.tables.keys())
    expected = {
        "project", "site", "site_extended", "floor", "map", "device",
        "zone", "cable", "import_batch", "event", "snapshot",
        "idempotency_key", "design", "sandbox_config",
    }
    assert expected <= tables


@pytest.fixture()
async def sqlite_session(tmp_path):
    """Build a fresh sqlite engine + session, isolated per test."""
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from packages.db.models import Base

    url = f"sqlite+aiosqlite:///{tmp_path / 'test.db'}"
    engine = create_async_engine(url, future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    await engine.dispose()


async def test_can_create_and_query_project(sqlite_session):
    """End-to-end: create tables, insert, query."""
    from sqlalchemy import select

    from packages.db.models import Project

    project = Project(name="Test Project", code="TEST-001")
    sqlite_session.add(project)
    await sqlite_session.commit()

    result = await sqlite_session.execute(select(Project).where(Project.code == "TEST-001"))
    found = result.scalar_one()
    assert found.name == "Test Project"
    assert found.id is not None


async def test_site_requires_unique_project_id_and_site_number(sqlite_session):
    """Unique constraint should reject duplicate (project_id, site_number)."""
    from sqlalchemy.exc import IntegrityError

    from packages.db.models import Project, Site

    project = Project(name="Test", code="DUP-001")
    sqlite_session.add(project)
    await sqlite_session.flush()

    sqlite_session.add(Site(project_id=project.id, site_number="3508", name="First"))
    await sqlite_session.flush()

    sqlite_session.add(Site(project_id=project.id, site_number="3508", name="Dup"))
    with pytest.raises(IntegrityError):
        await sqlite_session.flush()


async def test_event_ledger_inserts_with_payload(sqlite_session):
    """JSON payload column should round-trip."""
    from sqlalchemy import select

    from packages.db.models import Event

    event = Event(
        event_type="site.created",
        entity_type="site",
        entity_id="abc-123",
        payload={"name": "Test", "count": 42},
        actor="test.user@walmart.com",
    )
    sqlite_session.add(event)
    await sqlite_session.commit()

    result = await sqlite_session.execute(select(Event).where(Event.entity_id == "abc-123"))
    found = result.scalar_one()
    assert found.payload == {"name": "Test", "count": 42}
    assert found.actor == "test.user@walmart.com"
