# CadOwl / MAXILLM Architecture

## Architecture Style
- API-first modular monorepo
- Domain-driven packages for import/validation/gis/cable/ai
- Event-first write model for auditability

## Target Topology
- `apps/api`: synchronous API gateway + domain services
- `apps/worker`: async jobs (import parse/validate/export/ai review)
- `apps/web`: future UX shell (not built in this phase)
- `packages/*`: reusable domain engines
- `data/*`: schemas, rules, templates, fixtures

## Data Strategy
- PostgreSQL + PostGIS (target)
- Redis for queue/cache
- Object storage for source and export artifacts
- Event stream table for immutable audit

## Core Domain Aggregates
- Project aggregate (site/floor/map containment)
- Device and Cable aggregates
- Zone and Coordinate aggregates
- ImportBatch aggregate with validation artifacts

## Safety Controls
- Idempotency keys for bulk/import endpoints
- Soft delete + rollback points
- Mandatory event recording for mutating API calls
- AI mutations behind approval workflow

## Phase 1 Implementation Note
Current skeleton uses in-memory repositories for contract development speed. Replace with SQLAlchemy/PostgreSQL in Phase 1.1 without changing API contracts.
