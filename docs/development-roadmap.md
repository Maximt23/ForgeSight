# CadOwl Development Roadmap

## Proposed First Implementation Branch
`feature/phase1-api-foundation`

## Phase 0 (Architecture Lockdown)
Status: In progress via this change set
- [x] PRD baseline
- [x] Architecture baseline
- [x] Agent system model
- [x] API/import/validation/gis/cable/ai/doris specs (initial)
- [x] Repo structure normalized

## Phase 1 (Core Data + API Foundation)
- [x] Skeleton domain entities in API contracts
- [x] CRUD endpoints for core entities
- [x] Event logging on writes
- [x] Integration tests baseline
- [ ] DB migrations + PostgreSQL adapter
- [ ] Auth/RBAC middleware
- [ ] Idempotency + rate limit controls

## Phase 2 (Batch Import/Delete/Re-upload)
- [ ] Import batch state machine
- [ ] Parsing adapters (CSV/XLSX first)
- [ ] Validation quarantine and commit gating
- [ ] Rollback checkpoints and diff reports

## Phase 3+
Continue according to master directive phases 3-10.

## Engineering Quality Gates
- Unit + integration tests required per feature
- OpenAPI diff review on API changes
- Event schema backward compatibility checks
- No destructive operation without rollback metadata
