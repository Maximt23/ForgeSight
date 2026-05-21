# 🗄️ Database — PostgreSQL + Alembic

This directory contains the SQLAlchemy ORM models, Alembic migration
configuration, and async session factory for CadOwl's persistence layer.

## What's Here

```
packages/db/
├── __init__.py        # Re-exports get_session, engine
├── session.py         # Async engine + session factory + FastAPI dep
├── models.py          # SQLAlchemy 2.x ORM models
└── migrations/
    ├── env.py         # Alembic environment (async-aware)
    ├── script.py.mako # Migration template
    └── versions/      # Generated migration files
```

## Quick Start (Local Dev)

### 1. Start Postgres
```bash
docker compose up -d postgres
```

### 2. Run migrations
```bash
export DATABASE_URL="postgresql+asyncpg://cadowl:cadowl@localhost:5432/cadowl"
python -m scripts.migrate
```

Or with Alembic directly:
```bash
alembic upgrade head
```

### 3. Verify
```bash
python -c "
import asyncio
from sqlalchemy import text
from packages.db import async_session_factory

async def check():
    async with async_session_factory() as s:
        r = await s.execute(text('SELECT COUNT(*) FROM project'))
        print('Projects:', r.scalar())

asyncio.run(check())
"
```

## Common Operations

### Create a new migration after model changes
```bash
alembic revision --autogenerate -m "add foo column to bar"
# Review the generated file in packages/db/migrations/versions/
# Edit if needed (autogenerate is good but not perfect)
git add packages/db/migrations/versions/*.py
```

### Roll back one migration
```bash
alembic downgrade -1
```

### Check current revision
```bash
alembic current
```

### See full migration history
```bash
alembic history --verbose
```

### Reset everything (dev only!)
```bash
docker compose down -v postgres
docker compose up -d postgres
alembic upgrade head
```

## Configuration

Environment variables read by `session.py`:

| Variable | Default | Purpose |
|----------|---------|---------|
| `DATABASE_URL` | `postgresql+asyncpg://cadowl:cadowl@localhost:5432/cadowl` | Connection string |
| `SQL_ECHO` | `false` | Log all SQL (debug only) |
| `DB_POOL_SIZE` | `5` | Connection pool size |
| `DB_MAX_OVERFLOW` | `10` | Max overflow connections |
| `DB_POOL_RECYCLE_SECONDS` | `3600` | Recycle connections after this many seconds |

## Production Notes

### Connection string format
Always use the **async** driver prefix:
- ✅ `postgresql+asyncpg://...`
- ❌ `postgresql://...` (sync driver — won't work with the async engine)

### Migrations in containers
The Dockerfile copies the migration files. Run them at startup:

```yaml
# docker-compose.yml override or k8s init container
command: ["sh", "-c", "alembic upgrade head && uvicorn apps.api.main:app --host 0.0.0.0 --port 9010"]
```

Or as a separate Kubernetes Job that runs before the API deployment.

### Backups
PostgreSQL on the AI Innovation Lab is automatically backed up nightly
with PITR (point-in-time recovery). To restore, talk to AI Lab support.

For local dev backups:
```bash
docker exec cadowl-postgres pg_dump -U cadowl cadowl > backup.sql
```

## Adding a New Table

1. Add the model class to `packages/db/models.py`
2. Generate a migration: `alembic revision --autogenerate -m "add foo table"`
3. **Review the generated migration** (autogenerate misses some things like:
   - Server-side defaults
   - Enum types
   - Custom column types
4. Apply: `alembic upgrade head`
5. Commit the model + migration together in the same PR

## Testing

The session module uses a process-wide cache of the engine. Tests that
need to talk to a different DB should set `DATABASE_URL` **before**
importing anything from `packages.db`. See `tests/conftest.py`.

For unit tests of model logic, prefer SQLite in-memory:
```python
DATABASE_URL=sqlite+aiosqlite:///:memory:
```

Note that some PostgreSQL features (JSONB operators, partial indexes,
extensions) won't work on SQLite. Test those against a real Postgres
in integration tests.

## Migrating from JSON Store

The current `apps/api/store.py` uses an in-memory + JSON file backend.
The migration path:

1. **Phase 1.1.a**: Add SQLAlchemy models (done in this commit) ✅
2. **Phase 1.1.b**: Add a `JsonToSqlMigrator` that loads JSON files and
   bulk-inserts to Postgres
3. **Phase 1.1.c**: Replace `STORE.add_*` calls with session-based
   repositories
4. **Phase 1.1.d**: Delete `apps/api/store.py` and the JSON files
5. **Phase 1.1.e**: Update tests to use the database

See `docs/migrations/phase-1.1-postgres.md` for the full plan.
