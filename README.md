# CadOwl / MAXILLM

Enterprise security design operating system foundation.

## Status
This repository is transitioning from a CAD-to-SiteOwl converter utility into a modular, API-first platform.

## What Changed in This Foundation Update
- Added architecture/spec documentation under `docs/`
- Added monorepo folder layout for apps/packages/data/tests/infra
- Added Phase 1 API skeleton under `apps/api`
- Added JSON-backed storage under `data/jsondb`
- Added immutable event tracking for every write + append-only event ledger (`event_ledger.jsonl`)
- Added snapshot compaction + rollback endpoints (`/api/v1/revisions/*`)
- Added idempotency-key enforcement for import batch writes (`/api/v1/import/batch`)
- Added integration tests for contracts, persistence, idempotency, rollback, and event logging
- Added GitHub repo governance templates/workflow under `.github/`

## Repository Structure
```text
CadOwl/
  .github/
  apps/
    api/
    worker/
    web/
    mobile/
  packages/
  data/
    jsondb/
  docs/
  tests/
  scripts/
  infra/
```

## Phase 1 API Quick Start
```bash
cd C:\MAXILLM\cadowl
python -m uvicorn apps.api.main:app --reload --port 9010
```

Open API docs:
- http://localhost:9010/docs

## Run Tests
```bash
cd C:\MAXILLM\cadowl
python -m pytest tests/integration/test_phase1_api.py -q
```

## First Implementation Branch Proposal
`feature/phase1-api-foundation`

## Legacy Utility Notes
Legacy DXF conversion and SiteOwl CSV workflows remain present in root scripts and `cadowl/core/` modules. They should be progressively migrated into modular engines under `packages/`.

## Important Engineering Rules
- No silent success when failures occur
- Every mutating API action must emit event logs
- All core records are stored as JSON in `data/jsondb`
- Schema validation runs on writes using `apps/api/schemas_json/*.api.schema.json`
- Import/batch writes require `Idempotency-Key`
- Destructive workflows require rollback plans
- Keep adapters (CSV/CAD/PDF/SiteOwl) decoupled from internal domain model
