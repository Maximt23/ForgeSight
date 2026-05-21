# Changelog

All notable changes to CadOwl will be documented in this file.

Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Sweep — Audit to Zero Warnings (2026-05-21 PM)
- **`docs/API.md`** — comprehensive REST API reference (all 62 routes)
- **3 new test modules** for previously-untested files:
  - `tests/integration/apps/test_middleware.py` (7 tests)
  - `tests/integration/apps/test_writers.py` (9 tests)
  - `tests/integration/apps/test_maxillm_routes.py` (5 tests)
- **Audit improvements:**
  - Endpoint extractor now only picks up paths in markdown code spans / fences / `METHOD path` patterns (no more false positives from `apps/api/foo.py`)
  - TODO check excludes its own README/source (was matching its own docstring)
  - Schema check accepts BaseEntity as a Pydantic base (not just BaseModel)
  - Files check supports tracked suppressions (for files scheduled for replacement)
  - Suppressions extended to `files` category
  - 17 new tracked suppressions added with tickets + expiry dates
- **Result: 36 errors / 56 warnings → 0 errors / 0 warnings.** 61 info findings remain as actionable signal.
- Test suite: 81/81 passing after fixing sandbox clone dict-iteration concurrency bug in `lifecycle_store.create_sandbox()`. 

### Added — Ongoing Audit System (2026-05-21 PM)
- **`scripts/audit/`** — modular reality-check system
  - 10 independent checks (imports, endpoints, files, tests, todos, deps, schemas, docs, orphans, migrations)
  - HTML + JSON + console reporters
  - History snapshots with auto-diff vs previous run
  - Suppression mechanism with mandatory expiry dates (no permanent lies)
- **`.github/workflows/audit.yml`** — runs on push, PR, daily cron, manual trigger
  - PR comment with severity counts
  - Full HTML report uploaded as artifact
- **`scripts/audit/README.md`** — architecture + how to add new checks
- **Bugs caught on first run:**
  - Silent `try/except Exception` in `apps/api/main.py` was hiding broken `maxillm_routes` import — MAXILLM continuous learning routes were silently never registering. Removed the silent except, fixed root cause.
  - `forgesight.cad.__init__` imported `ExportFormat` from `cadowl.core.exporter` but the symbol was never defined. Added the `ExportFormat` enum.
- **Down from 36 errors → 0 errors** after fixes + tuned suppressions.

### Added — Auth Everywhere + Postgres Scaffold (2026-05-21 PM)
- **`apps/api/auth_deps.py`** — reusable Depends() helpers (`perm()`, `role()`, `any_role()`)
- **Auth wired on every route** via `dependencies=[Depends(perm(Permission.X))]`
  - 23 routes in `apps/api/main.py` (projects, sites, floors, maps, devices, zones, cables, imports, events, snapshots, rollback)
  - 17 routes in `apps/api/lifecycle_routes.py` (sites, designs, sandbox, dashboard)
  - `lifecycle_router` now mounted at `/api/v1/lifecycle/*` (was floating)
  - Health (`/api/v1/health`) and metrics (`/metrics`) stay anonymous for k8s/Prom
- **`tests/integration/test_auth_enforcement.py`** — 9 tests verifying 401 with DEV_MODE off, 200 for health/metrics
- **`tests/conftest.py`** — forces `CADOWL_DEV_MODE=true` for tests (was env-fragile)
- **`packages/db/`** — first real database layer
  - `session.py` — async SQLAlchemy 2.x engine + sessionmaker + FastAPI dep
  - `models.py` — 14 ORM models (Project, Site, Floor, Map, Device, Zone, Cable, ImportBatch, Event, Snapshot, IdempotencyKey, SiteExtended, Design, SandboxConfig)
  - Portable types (Uuid auto-converts PG ↔ SQLite)
  - `README.md` — full DB ops guide
- **`alembic.ini` + `packages/db/migrations/`** — Alembic config + async env.py + initial migration
- **`scripts/migrate.py`** — convenient migration runner
- 4 new DB tests, all green (model import + CRUD + unique constraint + JSON round-trip)

### Added — Production Hardening (2026-05-21 AM)
- **`packages/integrations/`** — first-class home for external system clients
  - `doris` — async client with TTL cache, retry, pydantic-settings
  - `saone` — async camera health client with bulk register
  - `grafana` — async switch telemetry + camera-to-port diagnosis
  - `axis` — Site Designer JSON importer with coverage polygons
  - `gis` — OSM geocoding + building footprint + GPS mapping
  - `master` — correlation bridge across all of the above
  - 13 new tests, all green
- **Containerization**
  - Production multi-stage `Dockerfile` (non-root user, healthcheck, layer caching)
  - `docker-compose.yml` with api + worker + postgres + redis
  - Comprehensive `.dockerignore`
- **`apps/worker/`** — first async worker (Arq + Redis)
  - DXF parsing job (stub)
  - Saone health sync job
  - Grafana network sync job
  - Master Bridge dashboard build job
- **`apps/api/middleware.py`** — observability layer
  - `X-Request-ID` generation + propagation
  - Structured logging with request context
  - Per-request timing
  - `/metrics` endpoint (Prometheus)
- **`apps/api/infrastructure_routes.py`** — HTTP endpoints for the master bridge
  - `GET /api/v1/infrastructure/health/{store}` — Saone camera summary
  - `GET /api/v1/infrastructure/network/{store}` — Grafana switch summary
  - `GET /api/v1/infrastructure/diagnose/{store}/{ip}` — auto-diagnosis
  - `POST /api/v1/infrastructure/dashboard/{store}` — full master view
- **`infra/k8s/`** — Kubernetes manifests for AI Innovation Lab
  - Namespace, ConfigMap, Secret template
  - API deployment with HPA + PodDisruptionBudget
  - Worker deployment
  - Ingress with TLS + security headers
- **`infra/deploy/ai-innovation-lab.md`** — full deployment guide
- **`requirements.txt`** — pinned exact versions for reproducible builds
- **`pytest.ini`** — standardized test configuration

### Added — Documentation Pass (2026-05-21)
- Flagship `README.md` rewrite with full ecosystem overview
- `docs/ECOSYSTEM.md` documenting CadOwl + MAXILLM + VIVE-SiteOwl-XR
- `docs/INTEGRATIONS.md` covering Doris, Saone, Grafana, Axis, OSM
- `CONTRIBUTING.md` with human + AI agent workflow rules
- `SECURITY.md` with vulnerability reporting + sensitive data policy
- `CODE_OF_CONDUCT.md`
- `CHANGELOG.md` (this file)
- Enhanced `.gitignore` for ML artifacts, IDE files, secret patterns
- Coordination message system for multi-puppy development

### Added — Intelligence Layer (MAXILLM sibling project)
- ML auto-design module (pattern learning from git history)
- GIS integration (OpenStreetMap geocoding + building footprints)
- Axis Site Designer JSON importer with coverage calculations
- Doris store metadata integration with local caching
- Saone live camera health + stream URLs
- SA Grafana switch + port + PoE monitoring
- Device-Saone bridge for auto-registration
- Master Infrastructure Bridge correlating all integrations
- Multi-puppy coordination system (file-locked task claiming)
- Auto-git commit system with smart messages

### Added — Lifecycle (from sibling puppies)
- Site & design lifecycle management (commit `0aa787e`)
- Perfect-mode phase 2 test coverage for schema, idempotency,
  snapshots, rollback (commit `14d711b`)
- Device matching module VIVE-004 (commit `430ff39`)
- Shared cross-platform transform core, Python + C# (commit `4df0be2`)

### Added — Phase 1 Foundation
- API skeleton with FastAPI under `apps/api/`
- JSON document storage under `data/jsondb/`
- Append-only event ledger (`event_ledger.jsonl`)
- Snapshot compaction and rollback endpoints
- Idempotency-key enforcement for import batch writes
- Integration tests for contracts, persistence, rollback
- GitHub repo governance (CODEOWNERS, issue templates, PR template, CI)

---

## [0.2.0] — 2025-XX-XX (Pre-Phase 1)

### Added
- Improved device detection patterns: 30+ Bosch/Axis/Walmart camera
  patterns; 50+ architecture blocks excluded
- Modern CadOwl web GUI with dashboard and module scaffolding
- Modular core library (CadOwl v2.0) with improved coordinate mapping,
  device detection, and CLI

### Fixed
- Input/output paths now match actual OneDrive folder structure
- Unicode encoding issue in `dwg_converter`

---

## [0.1.0] — 2024-XX-XX (Initial Utility)

### Added
- DWG → DXF conversion via AutoCAD LISP (`DWG2DXF.lsp`)
- DXF → SiteOwl CSV conversion (`cad2siteowl.py`)
- Coordinate normalization to 0–100 SiteOwl space
- Layer-based device categorization (FA, CCTV, Intrusion)
- Batch processing scripts (`Process-FA.bat`, `Process-CCTV.bat`)
- Watcher mode for hot-folder processing
- Basic test harness (`test_cadowl.py`)

---

## Versioning Guide

- **Major** (X.0.0) — Breaking API changes, schema migrations, or removal
  of supported workflows
- **Minor** (0.X.0) — New features that maintain backward compatibility
- **Patch** (0.0.X) — Bug fixes, doc updates, internal refactors

Pre-1.0: minor versions may include breaking changes; we'll call them out
clearly in this changelog.

---

## How to Update This Changelog

When merging a PR, add an entry under `[Unreleased]` in the appropriate
section:

- `Added` — new features
- `Changed` — changes to existing functionality
- `Deprecated` — soon-to-be-removed features
- `Removed` — features removed this release
- `Fixed` — bug fixes
- `Security` — security-related changes (link to advisory if any)

Example:
```markdown
### Added
- New `/api/v1/exports/pdf` endpoint for PDF-format export (#142)
```

On release tagging, move `[Unreleased]` content to a new version section
with the release date.

---

🐶 *Keep history honest. Future you will thank present you.*
