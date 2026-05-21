# CadOwl / MAXILLM

Enterprise security design operating system foundation.

## Status
This repository is transitioning from a CAD-to-SiteOwl converter utility into a modular, API-first platform.

## What Changed in This Foundation Update
- Added architecture/spec documentation under `docs/`
- Added monorepo folder layout for apps/packages/data/tests/infra
- Added Phase 1 API skeleton under `apps/api`
- Added integration tests for API contracts and event logging

## Repository Structure
```text
CadOwl/
  apps/
    api/
    worker/
    web/
  packages/
  data/
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
- Destructive workflows require rollback plans
- Keep adapters (CSV/CAD/PDF/SiteOwl) decoupled from internal domain model
